"""Build the deepresearch-ready markdown prompt from Stage 1+2 data.

The prompt is composed in three sections so the truncation logic always
preserves the critical instructions (header context + output preferences),
shrinking only the per-branch detail when over the 2000-char cap.
"""
from __future__ import annotations
import json
import re

_MAX_CHARS = 2000


def build_handoff_prompt(stage_data: dict, project_name: str) -> tuple[str, bool]:
    """
    Build a markdown research brief from stage_data collected in Stage 1+2.

    Returns (prompt_str, truncated_bool).
    """
    central_question = stage_data.get("central_question", "")
    audience = stage_data.get("audience", "client")
    desired_decision = stage_data.get("desired_decision", "")
    situation = stage_data.get("situation", "")
    complication = stage_data.get("complication", "")
    language = _resolve_language(stage_data.get("language", stage_data.get("output_language", "")))

    branches = _parse_branches(stage_data.get("branches", ""))[:3]

    head = _render_head(project_name, central_question, audience, desired_decision, situation, complication)
    tail = _render_tail(language)

    # First attempt: full detail (sub-questions + full evidence)
    body = _render_branches(branches, include_sub_questions=True, max_evidence_chars=None)
    prompt = f"{head}\n\n{body}\n\n{tail}"
    if len(prompt) <= _MAX_CHARS:
        return prompt, False

    # Shrink #1: drop sub-questions
    body = _render_branches(branches, include_sub_questions=False, max_evidence_chars=None)
    prompt = f"{head}\n\n{body}\n\n{tail}"
    if len(prompt) <= _MAX_CHARS:
        return prompt, True

    # Shrink #2: cap evidence text
    fixed = len(head) + len(tail) + len("\n\n") * 2
    per_branch_budget = max(80, (_MAX_CHARS - fixed) // max(1, len(branches)) - 80)
    body = _render_branches(branches, include_sub_questions=False, max_evidence_chars=per_branch_budget)
    prompt = f"{head}\n\n{body}\n\n{tail}"
    if len(prompt) <= _MAX_CHARS:
        return prompt, True

    # Last resort: hard truncate body, keep head + tail
    body_max = _MAX_CHARS - fixed - 50  # 50 chars for ellipsis note
    body = body[:body_max].rsplit("\n", 1)[0] + "\n…(detail trimmed to fit)"
    prompt = f"{head}\n\n{body}\n\n{tail}"
    return prompt, True


def _render_head(project_name: str, central_question: str, audience: str,
                  desired_decision: str, situation: str, complication: str) -> str:
    return "\n".join([
        f"# Research Brief — {project_name}",
        "",
        "## Central question",
        central_question or "(not yet defined)",
        "",
        "## Audience & decision context",
        f"- **Audience:** {_prettify(audience)}",
        f"- **Desired decision:** {desired_decision or '(not yet defined)'}",
        "",
        "## Background",
        f"- **Situation (what we know):** {situation or '(see engagement context)'}",
        f"- **Complication (what creates urgency):** {complication or '(see engagement context)'}",
    ])


def _render_branches(branches: list[dict], include_sub_questions: bool,
                       max_evidence_chars: int | None) -> str:
    lines: list[str] = ["## MECE structure — investigate these 3 branches", ""]
    letters = ["A", "B", "C"]
    for i, branch in enumerate(branches):
        letter = letters[i] if i < len(letters) else str(i + 1)
        question = branch.get("question", f"Branch {letter}")
        evidence = branch.get("evidence") or branch.get("evidence_needed", "")
        so_what = branch.get("so_what", "")

        if max_evidence_chars and len(evidence) > max_evidence_chars:
            evidence = evidence[:max_evidence_chars].rstrip(" ,;") + "…"

        lines.append(f"### Branch {letter} — {question}")
        lines.append(f"- **Evidence needed:** {evidence or '(to be researched)'}")
        lines.append(f"- **So-what we expect:** {so_what or '(to be determined)'}")

        if include_sub_questions:
            subs = _extract_sub_questions(evidence)
            if subs:
                lines.append("- **Sub-questions:**")
                for sq in subs[:3]:
                    lines.append(f"  - {sq}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _render_tail(language: str) -> str:
    return "\n".join([
        "## Output preferences",
        "- **Depth:** comprehensive (run all 4 rounds: thematic → entities → recipient → synthesis)",
        "- **Format:** structured report with citations [N], one section per MECE branch + executive summary",
        f"- **Language:** {language}",
        "- **Quality bar:** Tier-1 sources only (official institutions, top-tier consultancies, peer-reviewed academic). No blogs, no Wikipedia.",
    ])


def _parse_branches(raw) -> list[dict]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    return []


def _extract_sub_questions(evidence: str) -> list[str]:
    """Split evidence text into 2-3 sub-questions, respecting parenthesis depth.

    A comma or semicolon inside parens is NOT a split point — that prevents
    fragments like ``downside (FX`` when the source reads
    ``downside (FX, regulatory, talent), exit options``.
    """
    if not evidence:
        return []
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in evidence:
        if ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch in ",;\n" and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))

    result: list[str] = []
    for p in parts:
        p = re.sub(r"^\s*\d+\.\s*", "", p).strip().strip("-•").strip()
        if len(p) > 4:
            if not p.endswith("?"):
                p = p.rstrip(".") + "?"
            result.append(p)
    return result[:3]


def _resolve_language(lang_code: str) -> str:
    mapping = {
        "es": "Spanish", "en": "English", "pt": "Portuguese",
        "fr": "French", "de": "German", "it": "Italian",
    }
    if not lang_code:
        return "English"
    lower = lang_code.lower()
    return mapping.get(lower, lang_code)


def _prettify(value: str) -> str:
    known = {
        "board": "Board / C-suite", "client": "Client (external)",
        "working_team": "Working Team", "steering": "Steering Committee",
    }
    return known.get(value.lower() if value else "", value or "client")
