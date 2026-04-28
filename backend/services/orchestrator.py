"""
2-Stage MECE Orchestrator — Stage 1 (Define Problem) + Stage 2 (MECE Structure).

Upgraded to deepresearch-quality prompts:
- XML-tagged context (chunks, web results)
- Self-check blocks for quality assurance
- Depth-aware instructions
- Citation system [N] for traceability
"""
from __future__ import annotations
import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.engagement_templates import EngagementTemplate

def detect_language(text: str) -> str:
    """Simple language detection: Spanish vs English."""
    es_words = {"el", "la", "los", "las", "de", "del", "en", "un", "una", "que", "por",
                "para", "con", "como", "es", "son", "puede", "debe", "esta", "este",
                "empresa", "mercado", "costo", "inversion", "debemos", "queremos", "necesitamos"}
    words = set(text.lower().split())
    es_count = len(words & es_words)
    return "es" if es_count >= 3 else "en"

STAGE_NAMES = {
    1: "Define Problem",
    2: "MECE Structure",
}

MECE_TEMPLATES_TEXT = {
    "market_entry": "1. Is the market attractive? (TAM, growth, barriers)\n2. Can we win? (competition, advantage, capabilities needed)\n3. Is it worth the investment? (ROI, timeline, risk mitigation)",
    "cost_reduction": "1. Where are the largest cost pools? (breakdown, benchmark vs peers)\n2. What are the actionable levers? (eliminate, optimize, automate)\n3. How do we implement and sustain? (sequence, governance, tracking)",
    "growth_strategy": "1. Where is growth coming from? (organic, new markets, adjacencies)\n2. What do we need to invest? (capabilities, M&A, capital)\n3. What is the risk-adjusted return? (scenarios, sensitivity, go/no-go)",
    "digital_transformation": "1. Where is digital creating the most value? (automation, data, journeys)\n2. What is our digital maturity gap? (benchmark, infra, talent)\n3. What is the transformation roadmap? (quick wins, sequence, metrics)",
    "generic": "1. What is the current state and why does it matter?\n2. What are the options and trade-offs?\n3. What should we do and how?",
}

# ---------------------------------------------------------------------------
# Context formatting (deepresearch-style XML tags)
# ---------------------------------------------------------------------------

def _format_pdf_context(pdf_text: str) -> str:
    """Format PDF content as XML chunks for structured citation."""
    if not pdf_text:
        return ""
    pages = re.split(r'\[Page (\d+)\]', pdf_text)
    chunks = []
    idx = 1
    for i in range(1, len(pages), 2):
        page_num = pages[i]
        text = pages[i + 1].strip()[:2000] if i + 1 < len(pages) else ""
        if text:
            chunks.append(f'<chunk index="{idx}" source="Uploaded PDF" page="{page_num}">\n{text}\n</chunk>')
            idx += 1
    if not chunks and pdf_text:
        chunks.append(f'<chunk index="1" source="Uploaded PDF">\n{pdf_text[:8000]}\n</chunk>')
    return "\n\n".join(chunks)


def _format_web_context(web_text: str, offset: int = 0) -> str:
    """Format web search results as XML for structured citation."""
    if not web_text:
        return ""
    results = re.split(r'\[Web \d+\]', web_text)
    chunks = []
    idx = offset + 1
    for block in results:
        block = block.strip()
        if not block:
            continue
        lines = block.split('\n')
        title = lines[0].strip() if lines else ""
        url = ""
        snippet = ""
        for line in lines[1:]:
            if line.startswith("URL:"):
                url = line[4:].strip()
            else:
                snippet += line.strip() + " "
        if title or snippet:
            chunks.append(
                f'<web_result index="{idx}" title="{title}" url="{url}">\n{snippet.strip()}\n</web_result>'
            )
            idx += 1
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# Self-check block (deepresearch pattern)
# ---------------------------------------------------------------------------

_SELF_CHECK = """
<self_check>
Before outputting your response, silently verify:
1. The structure (branches, sub-questions, hypothesis) does NOT contain specific numbers, percentages, dollar amounts, dates, or company-specific quantitative claims. This app builds STRUCTURE ONLY. Real data comes from the deep-research run that happens AFTER this stage.
2. Each branch's `evidence` field is a list of WHAT TO INVESTIGATE (research categories, sub-questions) — NOT evidence already gathered. Phrasing example: "TAM 2026 estimate, growth rate vs LatAm peers, top 3 buyer segments, regulatory friction" (categories, not findings).
3. No `[N]` or `[Web N]` citations anywhere — citations belong in the deep-research output, not here.
4. The hypothesis is a logical "answer first" framed as a directional claim or conditional ("Entry is attractive IF X holds"), not a quantified one ("Entry yields $42M NPV").
5. Response language matches the user's language.
6. All JSON output is valid and parseable.
If any of these rules are violated, silently rewrite before outputting.
</self_check>"""

# ---------------------------------------------------------------------------
# Base system prompt
# ---------------------------------------------------------------------------

_BASE_SYSTEM = """You are a senior McKinsey engagement manager helping the user STRUCTURE a problem and DESIGN a research plan. You are NOT here to gather data — that happens later, in a separate deep-research run that uses the prompt this app produces.

<scope_of_this_app>
- Define the problem (Stage 1): central question, audience, decision context
- Build the MECE issue tree (Stage 2): branches with hypotheses + categories of evidence to investigate
- Output a markdown brief that another tool (deepresearch) consumes to do the actual investigation

YOU DO NOT generate decks, slides, action titles, charts, or quantified findings. Those live downstream.
</scope_of_this_app>

<rules>
1. **Answer First (Pyramid Principle):** Frame the hypothesis as a directional "answer first" — but conditional, NOT quantified. ("Entry is attractive IF the GTM partnership compresses time-to-market" — NOT "Entry yields $42M NPV").
2. **MECE:** Every branch grouping is Mutually Exclusive (no overlap) and Collectively Exhaustive (no gaps). Test: can every conceivable evidence category fit in exactly one branch?
3. **No data, no citations:** This app does NOT have real data and does NOT need it. Do not write specific numbers ($, %, dates, market sizes). Do not write `[N]` or `[Web N]` citations. If a number sneaks into your draft, silently remove it before outputting.
4. **Research-readiness:** Each branch's evidence field is a LIST OF QUESTIONS / DATA CATEGORIES the downstream researcher must hunt for, not findings. Think "what would I need to know to test this branch?" — not "what do I already know?".
5. **So-What test:** Each branch's `so_what` says how the answer to that branch shapes the final decision (e.g. "Confirms whether the 5-year revenue prize justifies entry costs"). It is a logical implication, not a numeric claim.
</rules>

Respond in the same language the user uses. Be directive and efficient — act like a partner scoping an engagement, not running it.

<interactive_options>
CRITICAL: Whenever you ask the user a question or need their input, you MUST end your response with a hidden options block containing exactly 10 suggested answers. The options must be contextually relevant, specific, and varied — ranging from common choices to creative alternatives. Use this EXACT format as the very last thing in your response:

<!-- OPTIONS_JSON: ["option 1", "option 2", ..., "option 10"] -->

Rules:
- Always generate exactly 10 options
- Options must be in the same language as the conversation
- Options should be complete, ready-to-send answers (not single words)
- Make options progressively more specific/creative (first 3 general, next 4 domain-specific, last 3 creative/niche)
- If asking about audience/deck_type, map options to the available values
- For open-ended questions (central_question, desired_decision), suggest realistic consulting scenarios based on uploaded documents and context
- DO NOT include an "Other" option — the UI handles that automatically
- DO NOT mention these options in your visible text — they are only for the UI to render as buttons
</interactive_options>"""


def get_stage_prompt(stage: int, stage_data: dict, pdf_context: str = "",
                      storyline_context: dict = None, web_context: str = "",
                      output_tone: str = "professional", output_audience: str = "",
                      output_language: str = "",
                      engagement_template: "EngagementTemplate | None" = None) -> str:
    """Build the stage-specific system prompt with structured context."""

    doc_context = _format_pdf_context(pdf_context)
    web_ctx = _format_web_context(web_context)

    sources = ""
    if doc_context:
        sources += f"\n\n<document_sources>\n{doc_context}\n</document_sources>"
    if web_ctx:
        sources += f"\n\n<web_sources>\n{web_ctx}\n</web_sources>"

    output_opts = ""
    if output_tone and output_tone != "professional":
        tone_map = {
            "executive": "Write in crisp, authoritative executive style. No hedging. Lead with decisions.",
            "technical": "Use precise technical language. Include methodology details. Assume domain expertise.",
            "persuasive": "Emphasize impact, urgency, and ROI. Use power verbs. Build toward the ask.",
        }
        output_opts += f"\n<tone_directive>{tone_map.get(output_tone, '')}</tone_directive>"
    if output_audience:
        output_opts += f"\n<audience_override>Tailor all content for: {output_audience}</audience_override>"
    if output_language:
        lang_names = {"es": "Spanish", "en": "English", "pt": "Portuguese", "fr": "French", "de": "German"}
        output_opts += f"\n<language_directive>Respond ONLY in {lang_names.get(output_language, output_language)}.</language_directive>"

    if stage == 1:
        return _stage1_prompt(stage_data, sources + output_opts, engagement_template)
    elif stage == 2:
        return _stage2_prompt(stage_data, sources + output_opts, engagement_template)
    return _BASE_SYSTEM


def _stage1_prompt(data: dict, sources: str, engagement_template: "EngagementTemplate | None" = None) -> str:
    collected = "\n".join(f"- {k}: {v}" for k, v in data.items() if v) if data else "Nothing collected yet."

    template_context = ""
    if engagement_template:
        template_context = f"""

<template_context>
An engagement template has been selected: **{engagement_template.name}**
- deck_type is ALREADY SET to: **{engagement_template.deck_type}** (do NOT ask)
- audience is ALREADY SET to: **{engagement_template.default_audience}** (do NOT ask)

You only need to collect 2 things:
1. **central_question** -- the specific question this deck answers
2. **desired_decision** -- the concrete decision the audience should make

IMPORTANT: When the user provides both (or says "confirmo"/"confirma"/"avanza"/"si"), immediately output the JSON block with all 4 fields (using the pre-set deck_type and audience) and advance. Do NOT ask additional questions about context, strategy, or anything else. Move fast.
</template_context>"""

    return f"""{_BASE_SYSTEM}

<stage>Stage 1: Define the Problem</stage>

<objective>
Collect 4 required inputs from the user to scope the engagement. Ask ONE question at a time. Be conversational but push for specificity.
</objective>

<required_inputs>
1. **central_question** -- The ONE question this deck answers. Must be specific and decision-oriented.
   BAD: "What about our market?" / GOOD: "Should we enter the Latin American market in 2026?"
2. **audience** -- Options: board, client, working_team, steering
3. **deck_type** -- Options: strategic, diagnostic, market_entry, due_diligence, transformation, progress_update, implementation
4. **desired_decision** -- The concrete decision the audience should make.
   BAD: "Understand the market" / GOOD: "Approve $10M investment in Brazil operations"
</required_inputs>

<collected_so_far>
{collected}
</collected_so_far>
{template_context}
<instructions>
- If the user provides multiple answers at once, acknowledge all of them and IMMEDIATELY output the JSON
- If a PDF is uploaded, use it as CONTEXT (their internal memo or brief) to ask sharper questions — but do NOT extract specific data or cite the document; this stage is about scoping, not analysis
- When all 4 are collected (or 2 when template is active), present a brief summary and output the JSON block IN THE SAME MESSAGE. Do NOT wait for a separate confirmation message.
- If the user says "confirmo", "si", "avanza", "advance", or similar — output the JSON immediately
- On confirmation, output a JSON block with the 4 fields:
```json
{{"central_question": "...", "audience": "...", "deck_type": "...", "desired_decision": "..."}}
```
CRITICAL: Once you have enough information, output the JSON. Do not ask follow-up questions about strategic context, ROI targets, or organizational details. Those are nice-to-have, not blockers.
</instructions>
{sources}"""


def _stage2_prompt(data: dict, sources: str, engagement_template: "EngagementTemplate | None" = None) -> str:
    question = data.get("central_question", "Not defined")
    audience = data.get("audience", "client")
    deck_type = data.get("deck_type", "strategic")

    if engagement_template and engagement_template.mece_branches:
        template = engagement_template.id
        branch_lines = []
        for i, branch in enumerate(engagement_template.mece_branches, 1):
            q = branch.get("question", "")
            evidence = branch.get("evidence_needed", "")
            so_what = branch.get("so_what_template", "")
            branch_lines.append(
                f"{i}. {q}\n   Evidence needed: {evidence}\n   So-what template: {so_what}"
            )
        template_text = "\n".join(branch_lines)
    else:
        q_lower = question.lower()
        if any(w in q_lower for w in ["enter", "market", "expand", "country", "region"]):
            template = "market_entry"
        elif any(w in q_lower for w in ["cost", "reduce", "save", "efficiency", "optimize"]):
            template = "cost_reduction"
        elif any(w in q_lower for w in ["grow", "growth", "revenue", "scale"]):
            template = "growth_strategy"
        elif any(w in q_lower for w in ["digital", "transform", "automate", "ai", "technology"]):
            template = "digital_transformation"
        else:
            template = "generic"
        template_text = MECE_TEMPLATES_TEXT.get(template, MECE_TEMPLATES_TEXT["generic"])

    stage2_additions = ""
    if engagement_template and engagement_template.stage2_additions:
        stage2_additions = f"\n{engagement_template.stage2_additions}"

    return f"""{_BASE_SYSTEM}

<stage>Stage 2: MECE Structure & Hypothesis (no data, structure only)</stage>

<context>
Central question: {question}
Audience: {audience} | Deck type: {deck_type}
</context>

<objective>
Decompose the central question into a MECE issue tree. For each branch, define:
  (a) the sub-question that branch answers
  (b) what the deep-research run will need to investigate (a list of categories / sub-questions, NOT findings)
  (c) the "so-what" implication if that branch resolves a particular way

Then formulate ONE governing hypothesis — the "answer first" — phrased as a conditional or directional claim.

Default to **3 branches** (McKinsey norm). 4–5 only if the question genuinely doesn't fit in 3, or if the user asks. When the user requests N branches, deliver N.

After Stage 2 is confirmed, this app produces a markdown research brief that the user pastes into deepresearch. **The downstream researcher needs structure, not pre-cooked answers.** Resist the temptation to "be helpful" by guessing numbers — that pollutes the brief and biases the research.
</objective>

<suggested_template>
{template_text}
</suggested_template>
{stage2_additions}
<instructions>
1. Present **N branches** adapted to the user's specific context (default 3). For each branch, output: `question`, `evidence` (list of research categories phrased as comma-separated nouns or short questions), `so_what` (logical implication, not a number).
2. State ONE `hypothesis` — directional or conditional. Examples: "Entry is attractive IF a local distribution partner compresses GTM by 9+ months" or "Cost reduction targets are achievable IF automation captures 60%+ of repetitive workflows". NEVER quantify the hypothesis itself.
3. Output the confirmed structure as JSON at the END of your message. Don't wait for a separate confirmation step.

CRITICAL: Always include the JSON block with `"confirmed": true` in your FIRST response in this stage. Present the structure AND the JSON together. The JSON `branches` array must include EVERY branch you described in prose.

```json
{{"mece_template": "{template}", "hypothesis": "...", "branches": [{{"question": "<sub-question this branch answers>", "evidence": "<comma-separated research categories the downstream investigator must look up>", "so_what": "<how the answer to this branch shapes the decision — logical, not numeric>"}}], "confirmed": true}}
```
</instructions>

<structure_rules>
**WRITE STRUCTURE, NOT FINDINGS.**

✅ GOOD examples of `evidence`:
  - "TAM 2026 estimate, growth rate vs LatAm peers, top 3 buyer segments, regulatory friction (LGPD)"
  - "Top 5 incumbent share, our differentiation, capability gaps in PT-BR support, partner ecosystem maturity"
  - "5-year NPV under 3 scenarios, payback period, downside drivers (FX / regulatory / talent), exit options"

❌ BAD examples of `evidence` (these contain findings — DO NOT WRITE THESE):
  - "TAM is $4.2B [Web 1], growing 21% YoY"          ← has data + citation
  - "TOTVS holds 24% market share"                    ← has data
  - "5y NPV $42M, payback 28 months"                  ← has data

✅ GOOD `hypothesis`:
  - "Brazil entry is attractive if we partner with a local BPO to compress GTM"
  - "Cost reduction targets are achievable if automation covers ≥60% of repetitive workflows"
  - "Three capability gaps prevent us from capturing the full opportunity"

❌ BAD `hypothesis`:
  - "Brazil entry yields $42M NPV with 28-month payback"  ← quantified
  - "We can capture 12% market share by 2028"             ← quantified

If the user uploads a PDF (their internal memo, brief, prior deck), you may **mention** items from it as context cues — but DO NOT cite them with [N] in this stage. The brief that goes to deepresearch should be clean of references; deepresearch will rebuild citations from its own sources.
</structure_rules>
{sources}
{_SELF_CHECK}"""


# ---------------------------------------------------------------------------
# Structured data extraction
# ---------------------------------------------------------------------------

def extract_structured_data(stage: int, response: str, current_data: dict) -> dict:
    """Extract structured data from the AI response using robust JSON parsing."""
    from .json_cleaner import clean_json_response

    result = {
        "collected_fields": {},
        "next_stage": stage,
        "storyline_update": None,
        "slides": None,
    }

    json_blocks = re.findall(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)

    parsed_data = []
    for block in json_blocks:
        try:
            parsed_data.append(json.loads(block))
        except json.JSONDecodeError:
            cleaned = clean_json_response(block)
            if cleaned and isinstance(cleaned, dict):
                parsed_data.append(cleaned)

    if not parsed_data:
        cleaned = clean_json_response(response)
        if cleaned and isinstance(cleaned, dict):
            parsed_data.append(cleaned)

    for data in parsed_data:

        if stage == 1:
            fields = {}
            for key in ["central_question", "audience", "deck_type", "desired_decision"]:
                if key in data:
                    fields[key] = data[key]
            if fields:
                result["collected_fields"] = fields
                merged = {**current_data, **fields}
                if all(merged.get(k) for k in ["central_question", "audience", "deck_type", "desired_decision"]):
                    result["next_stage"] = 2

        elif stage == 2:
            if data.get("confirmed"):
                fields = {}
                for key in ["mece_template", "hypothesis"]:
                    if key in data:
                        fields[key] = data[key]
                if "branches" in data:
                    fields["branches"] = json.dumps(data["branches"]) if isinstance(data["branches"], list) else data["branches"]
                result["collected_fields"] = fields
                # Stay at stage 2 — no stage 3 in this app. The handoff page is the next step.
                result["next_stage"] = 2

    return result
