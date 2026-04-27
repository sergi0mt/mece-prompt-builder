"""Self-refine service — iterative critique and improvement loop.
Deepresearch pattern: generate -> critique -> refine -> check quality gate.
Uses the unified LLM client for cost tracking."""
from __future__ import annotations
import json
from typing import AsyncGenerator
from .ai_service import complete

CRITIQUE_PROMPT = """You are a senior McKinsey partner reviewing a junior consultant's slide deck. Be ruthlessly honest. Score like a real partner — most first drafts score 50-65.

<task>
Review these slides and score them 0-100 on McKinsey quality. Then list specific weaknesses.
</task>

<scoring_criteria>
Score EACH dimension separately, then average:

1. **Action Titles (0-20 pts):**
   - 20pts: Every title is 8-11 words, contains a verb + quantified conclusion
   - 15pts: Most titles are action titles but some are topic labels
   - 10pts: Mixed — some action titles, some topic labels, some too long (>12 words)
   - 5pts: Mostly topic labels ("Market Analysis", "Cost Overview") with no conclusions
   - 0pts: Titles are just category names

   PER-SLIDE CHECK: For each slide with data, does the title reference the key number?
   BAD: "Revenue Analysis" with a chart showing 15% growth ✗
   GOOD: "Revenue grew 15% YoY, outpacing 8% industry average" ✓

2. **Data Quality (0-20 pts):**
   - 20pts: Every claim sourced with [N] or [Web N], no fabricated numbers
   - 15pts: Most claims sourced, a few uncited
   - 10pts: Some sources, some fabricated/unsourced numbers
   - 5pts: Few sources, numbers appear invented
   - 0pts: No sources, data appears entirely fabricated

3. **Bullet Concision (0-20 pts):**
   - 20pts: All bullets 3-8 words, use bold_prefix pattern, no full sentences
   - 15pts: Most bullets concise, a few wordy (10+ words)
   - 10pts: Mixed — some concise, some are full sentences (15+ words)
   - 5pts: Mostly full sentences, 15-25 words per bullet
   - 0pts: Paragraphs disguised as bullets

4. **Structure & Flow (0-20 pts):**
   - 20pts: Clear SCR → agenda → sections (with dividers) → rec → next steps; 40%+ charts
   - 15pts: Good structure but missing agenda or weak next steps
   - 10pts: Basic structure, too many consecutive text slides
   - 5pts: No clear sections, no dividers, all text
   - 0pts: Random slide order

5. **So-What & Insight Depth (0-20 pts):**
   - 20pts: Every chart has 2-3 sentence so-what connected to recommendation
   - 15pts: Most charts have so-what but some are generic ("market is growing")
   - 10pts: Some so-whats, some missing; connection to recommendation unclear
   - 5pts: Few or no so-whats; charts are data dumps without insight
   - 0pts: No charts or all charts lack annotation

TOTAL = sum of 5 dimensions (max 100)
</scoring_criteria>

<slides>
{slides_json}
</slides>

<output_format>
Respond with EXACTLY this JSON format:
```json
{{
  "score": <0-100>,
  "dimension_scores": {{
    "action_titles": <0-20>,
    "data_quality": <0-20>,
    "bullet_concision": <0-20>,
    "structure_flow": <0-20>,
    "so_what_depth": <0-20>
  }},
  "weaknesses": [
    {{"slide_index": <N>, "dimension": "action_titles|data_quality|bullet_concision|structure_flow|so_what_depth", "issue": "...", "suggestion": "..."}},
  ],
  "title_chart_mismatches": [
    {{"slide_index": <N>, "title_claims": "what the title says", "chart_shows": "what the chart actually shows"}}
  ],
  "overall_feedback": "..."
}}
```
</output_format>"""

REFINE_PROMPT = """You are a senior McKinsey consultant. Improve these slides to score 90+ based on the critique.

<original_slides>
{slides_json}
</original_slides>

<critique>
Score: {score}/100
Dimension scores: {dimension_scores}
Weaknesses:
{weaknesses}
Title-chart mismatches: {title_chart_mismatches}
Overall: {overall_feedback}
</critique>

<instructions>
Fix EVERY weakness. Apply these specific rules:

**Action Titles (target: 20/20):**
- Rewrite every topic label as a quantified conclusion: "[Subject] [verb] [number], [implication]"
- Target: 8-11 words per title
- If a slide has data, the title MUST reference the key number from that slide
- Use action verbs: "drives", "requires", "enables", "reduces", "captures" — NOT "is", "are", "has"

**Bullets (target: 20/20):**
- Rewrite every bullet to 3-8 words
- Use bold_prefix pattern: {{"bold_prefix": "Phase 1:", "text": "Launch Brazil Q2 2026"}}
- NO full sentences. Use FRAGMENTS: nouns, numbers, short phrases
- Max 4 bullets per slide

**Charts (target: 20/20):**
- Replace fabricated data with "[Estimated]" and explain basis
- so_what: Write 2-3 sentences connecting chart data to the recommendation
- Ensure every chart cites a source

**Structure (target: 20/20):**
- Include: title → exec summary → agenda → sections with dividers → recommendation → next steps
- No more than 2 consecutive content_text slides; alternate with charts
- At least 40% of content slides must have charts

**So-What (target: 20/20):**
- Every chart so_what must: (1) state the finding, (2) compare to benchmark, (3) connect to recommendation

Output the COMPLETE improved slide list as JSON:
```json
{{
  "slides": [
    {{"slide_type": "...", "action_title": "...", ...}},
  ]
}}
```
</instructions>"""


async def critique_slides(slides_json: str) -> dict | None:
    """Run a critique pass on the generated slides. Returns critique dict or None."""
    from .json_cleaner import clean_json_response

    prompt = CRITIQUE_PROMPT.format(slides_json=slides_json)
    resp = await complete(
        system_prompt="You are a McKinsey quality reviewer. Score harshly — most first drafts score 50-65.",
        user_prompt=prompt,
        task="critique",
    )
    return clean_json_response(resp.text)


async def refine_slides(slides_json: str, critique: dict) -> dict | None:
    """Refine slides based on critique. Returns improved slides dict or None."""
    from .json_cleaner import clean_json_response

    weaknesses_text = "\n".join(
        f"- Slide {w.get('slide_index', '?')} [{w.get('dimension', '')}]: {w.get('issue', '')} -> {w.get('suggestion', '')}"
        for w in critique.get("weaknesses", [])
    )

    mismatches_text = "\n".join(
        f"- Slide {m.get('slide_index', '?')}: Title claims '{m.get('title_claims', '')}' but chart shows '{m.get('chart_shows', '')}'"
        for m in critique.get("title_chart_mismatches", [])
    ) or "None"

    dimension_scores = json.dumps(critique.get("dimension_scores", {}))

    prompt = REFINE_PROMPT.format(
        slides_json=slides_json,
        score=critique.get("score", 0),
        dimension_scores=dimension_scores,
        weaknesses=weaknesses_text,
        title_chart_mismatches=mismatches_text,
        overall_feedback=critique.get("overall_feedback", ""),
    )

    resp = await complete(
        system_prompt="You are a McKinsey slide improvement specialist. Target 90+/100.",
        user_prompt=prompt,
        task="refine",
    )
    return clean_json_response(resp.text)


async def self_refine_loop(
    slides_json: str,
    max_passes: int = 2,
    quality_gate: int = 90,
) -> AsyncGenerator[dict, None]:
    """Run iterative critique-refine loop.

    Yields events:
    - {"type": "critique_start", "pass": N}
    - {"type": "critique_done", "score": N, "weaknesses": [...]}
    - {"type": "refine_start", "pass": N}
    - {"type": "refine_done", "slides": [...]}
    - {"type": "quality_gate_passed", "final_score": N}
    - {"type": "max_passes_reached", "final_score": N}
    """
    current_slides = slides_json
    last_score = 0

    for pass_num in range(1, max_passes + 1):
        # Critique
        yield {"type": "critique_start", "pass": pass_num}
        critique = await critique_slides(current_slides)

        if not critique:
            yield {"type": "critique_done", "score": 0, "weaknesses": [], "error": "Failed to parse critique"}
            break

        last_score = critique.get("score", 0)
        weaknesses = critique.get("weaknesses", [])
        yield {
            "type": "critique_done",
            "pass": pass_num,
            "score": last_score,
            "weaknesses": weaknesses,
            "dimension_scores": critique.get("dimension_scores", {}),
            "overall_feedback": critique.get("overall_feedback", ""),
        }

        # Quality gate check
        if last_score >= quality_gate:
            yield {"type": "quality_gate_passed", "final_score": last_score, "pass": pass_num}
            return

        # Refine
        yield {"type": "refine_start", "pass": pass_num}
        refined = await refine_slides(current_slides, critique)

        if refined and "slides" in refined:
            current_slides = json.dumps(refined["slides"], indent=2)
            yield {
                "type": "refine_done",
                "pass": pass_num,
                "slides": refined["slides"],
            }
        else:
            yield {"type": "refine_done", "pass": pass_num, "error": "Failed to parse refined slides"}
            break

    yield {"type": "max_passes_reached", "final_score": last_score}
