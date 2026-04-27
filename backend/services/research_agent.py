"""Research Agent — plan, step, synthesize pattern from deepresearch.

Three-phase research process:
1. PLAN: Generate research sub-questions from the central question + MECE branches
2. STEP: Execute focused search + deep fetch for each sub-question
3. SYNTHESIZE: Consolidate findings into a structured research brief

Returns a structured brief with citations, confidence scores, and data gaps.
Used automatically in stages 2-3 when research_depth is "detailed" or "comprehensive".
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator
from .ai_service import complete
from .web_search import search_web, deep_fetch_results, multi_lang_search, format_web_results
from .json_cleaner import clean_json_response

# ── Phase 1: Research Planning ──

PLAN_PROMPT = """You are a senior research analyst at McKinsey. Given a consulting question,
create a focused research plan.

<question>{question}</question>

<context>
Audience: {audience}
Deck type: {deck_type}
MECE branches: {branches}
Known data from documents: {known_data_summary}
</context>

<instructions>
Generate 3-6 specific research sub-questions that would provide the evidence needed
for a data-backed McKinsey presentation. Each sub-question should:
1. Target a specific data point, statistic, or insight
2. Be answerable through web search (not internal company data)
3. Map to one of the MECE branches
4. Include suggested search queries

Prioritize: market size data, growth rates, competitive benchmarks, industry trends,
and case studies.
</instructions>

<output_format>
```json
{{
  "research_plan": [
    {{
      "id": 1,
      "sub_question": "What is the current market size for X?",
      "branch": "Branch 1 name",
      "search_queries": ["query 1", "query 2"],
      "data_type": "market_size|growth_rate|benchmark|trend|case_study",
      "priority": "high|medium|low"
    }}
  ],
  "estimated_searches": <N>,
  "key_data_gaps": ["gap 1", "gap 2"]
}}
```
</output_format>"""


# ── Phase 3: Synthesis ──

SYNTHESIZE_PROMPT = """You are a senior McKinsey researcher. Synthesize these research findings
into a structured brief for the consulting team.

<question>{question}</question>

<research_findings>
{findings_text}
</research_findings>

<instructions>
Create a research brief that:
1. Summarizes key findings per MECE branch with specific numbers and sources
2. Rates confidence level for each finding (high/medium/low based on source quality)
3. Identifies remaining data gaps
4. Highlights the strongest evidence for the recommendation

Every finding MUST cite its source using [Web N] notation.
</instructions>

<output_format>
```json
{{
  "brief": {{
    "executive_summary": "2-3 sentence summary of key findings",
    "findings_by_branch": [
      {{
        "branch": "Branch name",
        "key_findings": [
          {{
            "finding": "Specific finding with numbers",
            "source": "[Web N] Source name",
            "confidence": "high|medium|low"
          }}
        ],
        "data_gaps": ["What we still don't know"]
      }}
    ],
    "strongest_evidence": ["Top 3 most compelling data points with citations"],
    "overall_confidence": "high|medium|low",
    "total_sources_used": <N>
  }}
}}
```
</output_format>"""


def _format_research_checklist(checklist: list) -> str:
    """Format a research checklist as a numbered list for prompt injection."""
    lines = []
    for i, item in enumerate(checklist, 1):
        # Support both ResearchQuestion objects and plain dicts
        q = item.question if hasattr(item, "question") else item.get("question", "")
        branch = item.branch if hasattr(item, "branch") else item.get("branch", "")
        priority = item.priority if hasattr(item, "priority") else item.get("priority", "medium")
        lines.append(f"{i}. [{priority.upper()}] {q} (branch: {branch})")
    return "\n".join(lines)


async def plan_research(
    question: str,
    audience: str = "client",
    deck_type: str = "strategic",
    branches: list[dict] | str = "",
    known_data: str = "",
    research_checklist: list | None = None,
) -> dict | None:
    """Phase 1: Generate a research plan with sub-questions and search queries."""
    branches_text = json.dumps(branches) if isinstance(branches, list) else str(branches)

    prompt = PLAN_PROMPT.format(
        question=question,
        audience=audience,
        deck_type=deck_type,
        branches=branches_text,
        known_data_summary=known_data[:2000] if known_data else "No prior data available",
    )

    # When a predefined research checklist is provided, inject it into the prompt
    if research_checklist:
        checklist_text = _format_research_checklist(research_checklist)
        prompt += f"""

<predefined_research_questions>
The engagement template provides these research questions as a starting point.
Use them as your foundation -- refine each for the specific context of this engagement,
and add 1-2 additional questions if you identify important gaps not covered below.

{checklist_text}
</predefined_research_questions>"""

    resp = await complete(
        system_prompt="You are a McKinsey research planning specialist.",
        user_prompt=prompt,
        task="research",
        max_tokens=2000,
    )
    return clean_json_response(resp.text)


async def execute_research_step(
    sub_question: dict,
    search_languages: list[str] | None = None,
) -> dict:
    """Phase 2: Execute a single research step — search + deep fetch.

    Returns enriched sub_question with search results and extracted evidence.
    """
    queries = sub_question.get("search_queries", [sub_question.get("sub_question", "")])
    all_results = []

    for query in queries[:3]:  # Max 3 queries per sub-question
        results = await search_web(query, max_results=5)

        # Multi-lang if specified
        if search_languages:
            for lang in search_languages:
                lang_results = await multi_lang_search(query, languages=[lang], max_results_per_lang=3)
                existing_urls = {r["url"] for r in results}
                results.extend(r for r in lang_results if r["url"] not in existing_urls)

        all_results.extend(results)

    # Deduplicate by URL
    seen = set()
    unique_results = []
    for r in all_results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique_results.append(r)

    # Sort by quality
    unique_results.sort(key=lambda r: r.get("quality_score", 0.5), reverse=True)
    unique_results = unique_results[:8]

    # Deep fetch Tier 1-2 sources
    enriched = await deep_fetch_results(unique_results, max_deep=2)

    return {
        **sub_question,
        "results": enriched,
        "result_count": len(enriched),
        "high_quality_count": sum(1 for r in enriched if r.get("quality_score", 0) >= 0.70),
    }


async def synthesize_findings(
    question: str,
    executed_steps: list[dict],
) -> dict | None:
    """Phase 3: Synthesize all research findings into a structured brief."""
    # Format findings as text for the LLM
    findings_parts = []
    web_idx = 1
    for step in executed_steps:
        findings_parts.append(f"\n## Sub-question: {step.get('sub_question', 'Unknown')}")
        findings_parts.append(f"Branch: {step.get('branch', 'Unknown')}")
        findings_parts.append(f"Priority: {step.get('priority', 'medium')}")
        findings_parts.append(f"Results found: {step.get('result_count', 0)} (high quality: {step.get('high_quality_count', 0)})")

        for r in step.get("results", []):
            tier_badge = {"high": "[HIGH-CRED]", "medium": "[MED-CRED]"}.get(r.get("quality_tier", ""), "")
            findings_parts.append(f"\n[Web {web_idx}] {tier_badge} {r['title']}")
            findings_parts.append(f"URL: {r['url']}")
            findings_parts.append(f"Snippet: {r['snippet']}")
            if r.get("deep_content"):
                findings_parts.append(f"Full content excerpt: {r['deep_content'][:800]}")
            web_idx += 1

    findings_text = "\n".join(findings_parts)

    prompt = SYNTHESIZE_PROMPT.format(
        question=question,
        findings_text=findings_text,
    )

    resp = await complete(
        system_prompt="You are a McKinsey research synthesis specialist.",
        user_prompt=prompt,
        task="final",
        max_tokens=3000,
    )
    return clean_json_response(resp.text)


async def run_research_agent(
    question: str,
    audience: str = "client",
    deck_type: str = "strategic",
    branches: list[dict] | str = "",
    known_data: str = "",
    search_languages: list[str] | None = None,
    max_steps: int = 6,
    research_checklist: list | None = None,
) -> AsyncGenerator[dict, None]:
    """Full research agent pipeline. Yields events for SSE streaming.

    Events:
    - {"type": "plan_start"}
    - {"type": "plan_done", "plan": {...}, "num_steps": N}
    - {"type": "step_start", "step_id": N, "sub_question": "..."}
    - {"type": "step_done", "step_id": N, "result_count": N, "high_quality": N}
    - {"type": "synthesize_start"}
    - {"type": "synthesize_done", "brief": {...}}
    - {"type": "research_complete", "total_sources": N}
    - {"type": "error", "message": "..."}
    """
    # Phase 1: Plan
    yield {"type": "plan_start"}
    try:
        plan = await plan_research(question, audience, deck_type, branches, known_data,
                                   research_checklist=research_checklist)
    except Exception as e:
        yield {"type": "error", "message": f"Planning failed: {e}"}
        return

    if not plan or "research_plan" not in plan:
        yield {"type": "error", "message": "Failed to generate research plan"}
        return

    steps = plan["research_plan"][:max_steps]
    yield {
        "type": "plan_done",
        "plan": plan,
        "num_steps": len(steps),
        "data_gaps": plan.get("key_data_gaps", []),
    }

    # Phase 2: Execute steps
    executed_steps = []
    for step in steps:
        step_id = step.get("id", len(executed_steps) + 1)
        yield {
            "type": "step_start",
            "step_id": step_id,
            "sub_question": step.get("sub_question", ""),
            "branch": step.get("branch", ""),
        }

        try:
            result = await execute_research_step(step, search_languages=search_languages)
            executed_steps.append(result)
            yield {
                "type": "step_done",
                "step_id": step_id,
                "result_count": result.get("result_count", 0),
                "high_quality": result.get("high_quality_count", 0),
            }
        except Exception as e:
            yield {"type": "step_done", "step_id": step_id, "error": str(e)}

    # Phase 3: Synthesize
    yield {"type": "synthesize_start"}
    try:
        brief = await synthesize_findings(question, executed_steps)
    except Exception as e:
        yield {"type": "error", "message": f"Synthesis failed: {e}"}
        return

    if brief and "brief" in brief:
        yield {"type": "synthesize_done", "brief": brief["brief"]}
        total_sources = sum(s.get("result_count", 0) for s in executed_steps)
        yield {"type": "research_complete", "total_sources": total_sources}
    else:
        yield {"type": "error", "message": "Failed to synthesize findings"}


def format_research_brief_for_prompt(brief: dict) -> str:
    """Format a research brief as structured context for the orchestrator prompts."""
    if not brief:
        return ""

    parts = ["\n<research_brief>"]
    parts.append(f"<executive_summary>{brief.get('executive_summary', '')}</executive_summary>")

    for branch in brief.get("findings_by_branch", []):
        parts.append(f"\n<branch name=\"{branch.get('branch', '')}\">\n<findings>")
        for finding in branch.get("key_findings", []):
            confidence = finding.get("confidence", "medium")
            parts.append(f"  [{confidence.upper()}] {finding.get('finding', '')} — {finding.get('source', '')}")
        parts.append("</findings>")
        if branch.get("data_gaps"):
            parts.append(f"<data_gaps>{', '.join(branch['data_gaps'])}</data_gaps>")
        parts.append("</branch>")

    if brief.get("strongest_evidence"):
        parts.append("\n<strongest_evidence>")
        for ev in brief["strongest_evidence"]:
            parts.append(f"  - {ev}")
        parts.append("</strongest_evidence>")

    parts.append(f"\n<confidence>{brief.get('overall_confidence', 'medium')}</confidence>")
    parts.append("</research_brief>")

    return "\n".join(parts)


# ── Persistence helpers ──


async def persist_research_state(
    project_id: str,
    plan: dict | None = None,
    sources: list | None = None,
    brief: dict | None = None,
    data_gaps: list | None = None,
    status: str | None = None,
):
    """Save research state to DB. Only updates non-None fields."""
    from ..database import get_db

    db = await get_db()
    try:
        # Check if a row already exists for this project
        cursor = await db.execute(
            "SELECT id FROM research_state WHERE project_id = ?", (project_id,)
        )
        existing = await cursor.fetchone()

        now = datetime.utcnow().isoformat()

        if not existing:
            # Create a new row with defaults, then update provided fields
            row_id = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO research_state (id, project_id, research_plan, research_brief, sources, data_gaps, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row_id,
                    project_id,
                    json.dumps(plan) if plan is not None else "{}",
                    json.dumps(brief) if brief is not None else "{}",
                    json.dumps(sources) if sources is not None else "[]",
                    json.dumps(data_gaps) if data_gaps is not None else "[]",
                    status or "pending",
                    now,
                    now,
                ),
            )
        else:
            # Build dynamic UPDATE for only the non-None fields
            updates = []
            values = []

            if plan is not None:
                updates.append("research_plan = ?")
                values.append(json.dumps(plan))
            if brief is not None:
                updates.append("research_brief = ?")
                values.append(json.dumps(brief))
            if sources is not None:
                updates.append("sources = ?")
                values.append(json.dumps(sources))
            if data_gaps is not None:
                updates.append("data_gaps = ?")
                values.append(json.dumps(data_gaps))
            if status is not None:
                updates.append("status = ?")
                values.append(status)

            if updates:
                updates.append("updated_at = ?")
                values.append(now)
                values.append(project_id)

                sql = f"UPDATE research_state SET {', '.join(updates)} WHERE project_id = ?"
                await db.execute(sql, values)

        await db.commit()
    finally:
        await db.close()


async def get_persisted_research(project_id: str) -> dict | None:
    """Load research state from DB. Returns None if no state exists."""
    from ..database import get_db

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM research_state WHERE project_id = ?", (project_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        # Parse JSON fields
        def _parse(val, default):
            if val is None:
                return default
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return default
            return val

        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "research_plan": _parse(row["research_plan"], {}),
            "research_brief": _parse(row["research_brief"], {}),
            "sources": _parse(row["sources"], []),
            "data_gaps": _parse(row["data_gaps"], []),
            "status": row["status"] or "pending",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    finally:
        await db.close()
