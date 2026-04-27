"""Build the deepresearch-ready markdown prompt from Stage 1+2 data."""
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

    branches = _parse_branches(stage_data.get("branches", ""))

    lines: list[str] = []
    lines.append(f"# Research Brief — {project_name}")
    lines.append("")
    lines.append("## Central question")
    lines.append(central_question or "(not yet defined)")
    lines.append("")
    lines.append("## Audience & decision context")
    lines.append(f"- **Audience:** {_prettify(audience)}")
    lines.append(f"- **Desired decision:** {desired_decision or '(not yet defined)'}")
    lines.append("")
    lines.append("## Background")
    lines.append(f"- **Situation (what we know):** {situation or '(see engagement context)'}")
    lines.append(f"- **Complication (what creates urgency):** {complication or '(see engagement context)'}")
    lines.append("")
    lines.append("## MECE structure — investigate these 3 branches")
    lines.append("")

    letters = ["A", "B", "C"]
    for i, branch in enumerate(branches[:3]):
        letter = letters[i]
        question = branch.get("question", f"Branch {letter}")
        evidence = branch.get("evidence") or branch.get("evidence_needed", "")
        so_what = branch.get("so_what", "")

        lines.append(f"### Branch {letter} — {question}")
        lines.append(f"- **Evidence needed:** {evidence or '(to be researched)'}")
        lines.append(f"- **So-what we expect:** {so_what or '(to be determined)'}")

        sub_questions = _extract_sub_questions(evidence)
        if sub_questions:
            lines.append("- **Sub-questions:**")
            for sq in sub_questions[:3]:
                lines.append(f"  - {sq}")
        lines.append("")

    lines.append("## Output preferences")
    lines.append("- **Depth:** comprehensive (run all 4 rounds: thematic → entities → recipient → synthesis)")
    lines.append("- **Format:** structured report with citations [N], one section per MECE branch + executive summary")
    lines.append(f"- **Language:** {language}")
    lines.append("- **Quality bar:** Tier-1 sources only (official institutions, top-tier consultancies, peer-reviewed academic). No blogs, no Wikipedia.")

    prompt = "\n".join(lines)

    if len(prompt) <= _MAX_CHARS:
        return prompt, False

    # Truncate gracefully at paragraph boundary
    truncated = prompt[:_MAX_CHARS]
    last_para = truncated.rfind("\n\n")
    if last_para > _MAX_CHARS // 2:
        truncated = truncated[:last_para]
    truncated += "\n\n*(prompt truncated to fit deepresearch character limit)*"
    return truncated, True


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
    """Split evidence text into 2-3 sub-questions by delimiter."""
    if not evidence:
        return []
    # Try splitting by comma, semicolon, or numbered list patterns
    parts = re.split(r'[;,]|\n+|\d+\.\s+', evidence)
    result = []
    for p in parts:
        p = p.strip().strip("-•").strip()
        if len(p) > 10:
            # Turn into a question if it doesn't end with ?
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
