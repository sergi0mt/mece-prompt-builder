"""Engagement Templates — data-driven definitions for 5 consulting engagement types.

Each template configures the orchestrator, research agent, and output pipeline
without changing their code. Templates are DATA, not logic.

The 5 templates:
1. Strategic Assessment
2. Commercial Due Diligence
3. Performance Improvement
4. Digital/Org Transformation
5. Market Entry / Growth Strategy
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ResearchQuestion:
    """A pre-defined research sub-question for the research agent."""
    question: str
    branch: str          # which MECE branch it maps to
    data_type: str       # market_size|benchmark|trend|case_study|regulatory|financial
    priority: str        # high|medium|low
    search_hints: list[str] = field(default_factory=list)


@dataclass
class EngagementTemplate:
    """Full configuration for one engagement type."""
    id: str
    name: str
    description: str
    icon: str                                    # lucide icon name for frontend

    # Research dimension
    research_checklist: list[ResearchQuestion]
    default_research_depth: str = "detailed"     # "detailed"|"comprehensive"
    recommended_domains: list[str] = field(default_factory=list)

    # Analysis dimension
    mece_branches: list[dict] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)

    # Stage customization (injected into orchestrator prompts)
    stage1_fields: list[str] = field(default_factory=list)  # extra fields beyond base 4
    stage2_additions: str = ""
    stage3_additions: str = ""

    # Deliverable dimension
    default_output_formats: list[str] = field(default_factory=list)
    deck_type: str = "strategic"
    slide_range: tuple[int, int] = (12, 18)
    default_audience: str = "client"


# ─────────────────────────────────────────────────────────────
# Template 1: Strategic Assessment
# ─────────────────────────────────────────────────────────────

STRATEGIC_ASSESSMENT = EngagementTemplate(
    id="strategic_assessment",
    name="Strategic Assessment",
    description="Evaluate an opportunity or strategic direction and recommend a course of action",
    icon="Compass",
    default_audience="board",
    deck_type="strategic",
    slide_range=(12, 16),
    default_output_formats=["strategy_deck", "executive_memo"],
    default_research_depth="detailed",
    frameworks=["porter_five_forces", "swot", "value_chain", "scenario_planning"],
    recommended_domains=["mckinsey.com", "hbr.org", "bcg.com", "economist.com"],

    mece_branches=[
        {
            "question": "Is the opportunity attractive and large enough to pursue?",
            "evidence_needed": "Market size, growth trajectory, demand drivers, macro trends",
            "so_what_template": "The [market/opportunity] represents $[X]B growing at [Y]%, driven by [drivers]",
        },
        {
            "question": "Can we realistically win given our capabilities and competition?",
            "evidence_needed": "Competitive landscape, our advantages/gaps, required capabilities",
            "so_what_template": "We have [advantage] but need to close gaps in [areas] to compete with [rivals]",
        },
        {
            "question": "Is it worth the investment given risks and returns?",
            "evidence_needed": "Required investment, expected ROI, risk factors, timeline",
            "so_what_template": "The investment of $[X]M yields [Y]% IRR over [Z] years with manageable risks",
        },
    ],

    research_checklist=[
        ResearchQuestion(
            question="What is the total addressable market size and growth forecast?",
            branch="opportunity_attractiveness",
            data_type="market_size",
            priority="high",
            search_hints=["[topic] market size forecast", "[topic] TAM SAM SOM", "[topic] industry growth rate"],
        ),
        ResearchQuestion(
            question="What are the key demand drivers and macro trends shaping this space?",
            branch="opportunity_attractiveness",
            data_type="trend",
            priority="high",
            search_hints=["[topic] industry trends", "[topic] demand drivers", "[topic] market dynamics"],
        ),
        ResearchQuestion(
            question="Who are the top 3-5 competitors and what is their positioning?",
            branch="ability_to_win",
            data_type="benchmark",
            priority="high",
            search_hints=["[topic] competitive landscape", "[topic] market share leaders", "[topic] key players"],
        ),
        ResearchQuestion(
            question="What capabilities or assets would we need to build or acquire?",
            branch="ability_to_win",
            data_type="benchmark",
            priority="medium",
            search_hints=["[topic] critical success factors", "[topic] capabilities needed", "[topic] barriers to entry"],
        ),
        ResearchQuestion(
            question="What is the typical investment required and expected returns?",
            branch="investment_worth",
            data_type="financial",
            priority="high",
            search_hints=["[topic] investment cost", "[topic] ROI benchmarks", "[topic] payback period"],
        ),
        ResearchQuestion(
            question="What are the primary risks and how have others mitigated them?",
            branch="investment_worth",
            data_type="case_study",
            priority="medium",
            search_hints=["[topic] risk factors", "[topic] failure cases", "[topic] lessons learned"],
        ),
    ],

    stage1_fields=["strategic_context"],

    stage2_additions="""
<template_guidance>
This is a STRATEGIC ASSESSMENT. The MECE structure must answer:
1. Is the opportunity attractive? (quantify market size, growth, timing)
2. Can we win? (competitive position, capabilities, differentiation)
3. Is it worth the investment? (ROI, risks, timeline)

Every branch must have at least one quantified data point. Avoid vague strategy language.
The hypothesis should state the recommended action clearly with scope and timeline.
</template_guidance>""",

    stage3_additions="""
<template_slide_rules>
Strategic Assessment deck structure:
1. Title slide
2. Executive Summary (SCR framework — lead with the recommendation)
3. Agenda (3 branches as sections)
4-5. Section 1: Market/Opportunity attractiveness (with sizing chart)
6-7. Section 2: Competitive position & capabilities (with benchmark chart)
8-9. Section 3: Investment case & risks (with financial chart)
10. Recommendations (prioritized, with owners and timeline)
11. Next Steps (concrete actions for next 30/60/90 days)
12. Appendix sources

Charts MUST include: at least one sizing chart (bar/waterfall), one competitive benchmark (harvey_balls or matrix_2x2), one financial chart (waterfall or line).
</template_slide_rules>""",
)

# ─────────────────────────────────────────────────────────────
# Template 2: Commercial Due Diligence
# ─────────────────────────────────────────────────────────────

COMMERCIAL_DUE_DILIGENCE = EngagementTemplate(
    id="commercial_due_diligence",
    name="Commercial Due Diligence",
    description="Analyze a target company or investment opportunity: market, competition, risks, and upside",
    icon="Search",
    default_audience="board",
    deck_type="due_diligence",
    slide_range=(18, 25),
    default_output_formats=["strategy_deck", "executive_memo", "one_pager"],
    default_research_depth="comprehensive",
    frameworks=["tam_sam_som", "porter_five_forces", "customer_segmentation", "synergy_model"],
    recommended_domains=["statista.com", "bloomberg.com", "sec.gov", "pitchbook.com"],

    mece_branches=[
        {
            "question": "Is the target's market attractive and growing?",
            "evidence_needed": "Market size, growth rate, segmentation, regulatory tailwinds/headwinds",
            "so_what_template": "The market is $[X]B growing at [Y]% with [positive/negative] regulatory trajectory",
        },
        {
            "question": "Is the target competitively positioned to sustain and grow?",
            "evidence_needed": "Market share, customer concentration, competitive moat, churn rate",
            "so_what_template": "The target holds [X]% share with [strong/weak] customer retention and [moat description]",
        },
        {
            "question": "Does the deal create value at the proposed price?",
            "evidence_needed": "Revenue multiples, synergy potential, integration risks, comparable transactions",
            "so_what_template": "At [X]x revenue, the deal creates value through [synergy type] synergies of $[Y]M",
        },
    ],

    research_checklist=[
        ResearchQuestion(
            question="What is the target market size and how is it segmented?",
            branch="market_attractiveness",
            data_type="market_size",
            priority="high",
            search_hints=["[industry] market size segmentation", "[industry] TAM forecast"],
        ),
        ResearchQuestion(
            question="What is the market growth rate and what drives it?",
            branch="market_attractiveness",
            data_type="trend",
            priority="high",
            search_hints=["[industry] growth rate drivers", "[industry] market forecast"],
        ),
        ResearchQuestion(
            question="Who are the key competitors and what is their market share?",
            branch="competitive_position",
            data_type="benchmark",
            priority="high",
            search_hints=["[industry] market share ranking", "[industry] competitive landscape"],
        ),
        ResearchQuestion(
            question="What is the customer concentration risk?",
            branch="competitive_position",
            data_type="financial",
            priority="high",
            search_hints=["[company] customer concentration", "[industry] customer base analysis"],
        ),
        ResearchQuestion(
            question="What are the revenue and EBITDA multiples for comparable deals?",
            branch="deal_value",
            data_type="financial",
            priority="high",
            search_hints=["[industry] M&A multiples", "[industry] transaction comparables"],
        ),
        ResearchQuestion(
            question="What synergy opportunities exist (revenue + cost)?",
            branch="deal_value",
            data_type="financial",
            priority="medium",
            search_hints=["M&A synergies [industry]", "post-merger integration synergies"],
        ),
        ResearchQuestion(
            question="What regulatory or legal risks could affect the deal?",
            branch="market_attractiveness",
            data_type="regulatory",
            priority="medium",
            search_hints=["[industry] regulation risk", "[industry] antitrust concerns"],
        ),
        ResearchQuestion(
            question="What are comparable transaction case studies and outcomes?",
            branch="deal_value",
            data_type="case_study",
            priority="medium",
            search_hints=["[industry] M&A case study", "[industry] acquisition outcomes"],
        ),
    ],

    stage1_fields=["target_company", "deal_size_estimate"],

    stage2_additions="""
<template_guidance>
This is a COMMERCIAL DUE DILIGENCE. The MECE structure must be investable:
1. Market attractiveness (size, growth, regulation) — is this a good market?
2. Competitive position (share, moat, customers) — is this a good company in that market?
3. Deal value (multiples, synergies, risks) — is this a good deal at this price?

Every finding must cite specific data. Estimates are acceptable ONLY if marked as [Estimated].
The hypothesis should clearly state whether the deal is attractive, with conditions.
</template_guidance>""",

    stage3_additions="""
<template_slide_rules>
Commercial Due Diligence deck structure:
1. Title slide (include "CONFIDENTIAL" marker)
2. Executive Summary (investment thesis — 1 slide)
3. Agenda
4-6. Market Analysis (sizing chart, growth chart, segmentation)
7-9. Competitive Position (market share, customer analysis, moat assessment)
10-12. Financial Assessment (multiples comparison, synergy waterfall, scenario analysis)
13. Key Risks & Mitigants (2-column layout)
14. Recommendations (Go/No-Go with conditions)
15. Next Steps (due diligence Phase 2 items)
16+. Appendix (data tables, source log)

MUST include: TAM/SAM/SOM chart, market share bar chart, comparable multiples table, synergy waterfall.
Mark all slides with "CONFIDENTIAL — For Discussion Purposes Only" in footer.
</template_slide_rules>""",
)

# ─────────────────────────────────────────────────────────────
# Template 3: Performance Improvement
# ─────────────────────────────────────────────────────────────

PERFORMANCE_IMPROVEMENT = EngagementTemplate(
    id="performance_improvement",
    name="Performance Improvement",
    description="Diagnose operational inefficiencies and design an improvement plan with quantified impact",
    icon="TrendingUp",
    default_audience="client",
    deck_type="diagnostic",
    slide_range=(16, 22),
    default_output_formats=["strategy_deck", "working_document"],
    default_research_depth="detailed",
    frameworks=["value_chain", "cost_tree", "benchmarking", "lean_six_sigma"],
    recommended_domains=["mckinsey.com", "deloitte.com", "gartner.com", "bls.gov"],

    mece_branches=[
        {
            "question": "Where are the largest cost pools and how do they compare to benchmarks?",
            "evidence_needed": "Cost breakdown, peer benchmarking, industry averages, growth trajectory of costs",
            "so_what_template": "[Cost category] represents [X]% of total costs, [Y]% above industry benchmark",
        },
        {
            "question": "What specific levers can drive measurable improvement?",
            "evidence_needed": "Improvement opportunities, automation potential, process redesign options, quick wins",
            "so_what_template": "[N] levers identified with combined potential savings of $[X]M ([Y]% of target)",
        },
        {
            "question": "How should we implement and sustain the improvements?",
            "evidence_needed": "Implementation roadmap, governance model, change management, tracking metrics",
            "so_what_template": "A [N]-phase implementation over [X] months will capture [Y]% of savings by Year 1",
        },
    ],

    research_checklist=[
        ResearchQuestion(
            question="What are the industry benchmark cost ratios for this sector?",
            branch="cost_pools",
            data_type="benchmark",
            priority="high",
            search_hints=["[industry] cost benchmarks", "[industry] operating cost ratio", "[industry] cost structure"],
        ),
        ResearchQuestion(
            question="What are the key operational metrics and how do peers perform?",
            branch="cost_pools",
            data_type="benchmark",
            priority="high",
            search_hints=["[industry] operational KPIs", "[industry] efficiency metrics", "[industry] peer comparison"],
        ),
        ResearchQuestion(
            question="What automation and process improvement technologies are available?",
            branch="improvement_levers",
            data_type="trend",
            priority="medium",
            search_hints=["[industry] automation opportunities", "[industry] process improvement technology"],
        ),
        ResearchQuestion(
            question="What are best-practice examples of similar improvement programs?",
            branch="improvement_levers",
            data_type="case_study",
            priority="medium",
            search_hints=["[industry] cost reduction case study", "operational improvement success story"],
        ),
        ResearchQuestion(
            question="What is the typical timeline and ROI for performance improvement programs?",
            branch="implementation",
            data_type="benchmark",
            priority="high",
            search_hints=["performance improvement program timeline", "cost reduction program ROI"],
        ),
        ResearchQuestion(
            question="What governance models sustain cost improvements long-term?",
            branch="implementation",
            data_type="case_study",
            priority="medium",
            search_hints=["cost reduction governance", "sustaining operational improvements"],
        ),
    ],

    stage1_fields=["target_improvement_pct", "cost_focus_area"],

    stage2_additions="""
<template_guidance>
This is a PERFORMANCE IMPROVEMENT diagnostic. The MECE structure must be actionable:
1. Where are the cost pools? (quantify each, benchmark vs peers — what's the gap?)
2. What levers exist? (specific, not generic — automation, consolidation, renegotiation, elimination)
3. How to implement? (phased roadmap with owners, milestones, tracking)

Every cost figure must be benchmarked against an industry reference. No unsubstantiated savings claims.
The hypothesis should state the total savings potential as a percentage and dollar amount.
</template_guidance>""",

    stage3_additions="""
<template_slide_rules>
Performance Improvement deck structure:
1. Title slide
2. Executive Summary (total savings potential + timeline)
3. Agenda
4-5. Current State: Cost breakdown & benchmark gaps (waterfall + bar chart)
6-8. Improvement Levers: 3-5 specific initiatives with impact sizing (stacked bar)
9-10. Implementation Roadmap: Phased timeline with milestones (timeline/gantt)
11. Quick Wins vs. Structural Changes (matrix_2x2)
12. Governance & Tracking: KPI dashboard design (harvey_balls)
13. Recommendations with savings by initiative
14. Next Steps (diagnostic deep-dive items)

MUST include: cost waterfall, benchmark comparison bar chart, implementation timeline, savings bridge.
</template_slide_rules>""",
)

# ─────────────────────────────────────────────────────────────
# Template 4: Digital/Org Transformation
# ─────────────────────────────────────────────────────────────

TRANSFORMATION = EngagementTemplate(
    id="transformation",
    name="Digital / Organizational Transformation",
    description="Design the future state (operating model, technology, processes) and build the transformation roadmap",
    icon="Layers",
    default_audience="client",
    deck_type="transformation",
    slide_range=(18, 25),
    default_output_formats=["strategy_deck", "executive_memo"],
    default_research_depth="detailed",
    frameworks=["maturity_model", "target_operating_model", "change_management", "agile_methodology"],
    recommended_domains=["mckinsey.com", "gartner.com", "forrester.com", "accenture.com"],

    mece_branches=[
        {
            "question": "Where is digital/organizational change creating the most value?",
            "evidence_needed": "Automation ROI, data-driven decision gains, customer journey improvements, revenue uplift",
            "so_what_template": "Digital creates [X]% efficiency gains in [areas], with $[Y]M revenue uplift from [initiative]",
        },
        {
            "question": "What is our current maturity gap vs. the target state?",
            "evidence_needed": "Maturity assessment, technology stack gaps, talent deficits, process inefficiencies",
            "so_what_template": "We score [X]/5 maturity vs. [Y]/5 industry leaders, with critical gaps in [areas]",
        },
        {
            "question": "What is the transformation roadmap to close the gap?",
            "evidence_needed": "Phased roadmap, investment requirements, quick wins, organizational changes needed",
            "so_what_template": "A [X]-year roadmap in [N] phases requires $[Y]M investment to reach target maturity",
        },
    ],

    research_checklist=[
        ResearchQuestion(
            question="What are the industry digital maturity benchmarks?",
            branch="value_creation",
            data_type="benchmark",
            priority="high",
            search_hints=["[industry] digital maturity index", "[industry] digital transformation benchmark"],
        ),
        ResearchQuestion(
            question="What technologies are driving the most value in this sector?",
            branch="value_creation",
            data_type="trend",
            priority="high",
            search_hints=["[industry] technology trends", "[industry] digital transformation ROI"],
        ),
        ResearchQuestion(
            question="What are successful transformation case studies in similar organizations?",
            branch="value_creation",
            data_type="case_study",
            priority="medium",
            search_hints=["[industry] digital transformation case study", "organizational transformation success"],
        ),
        ResearchQuestion(
            question="What are the common failure modes in transformation programs?",
            branch="maturity_gap",
            data_type="case_study",
            priority="medium",
            search_hints=["digital transformation failure reasons", "transformation program pitfalls"],
        ),
        ResearchQuestion(
            question="What talent and organizational changes are needed?",
            branch="maturity_gap",
            data_type="benchmark",
            priority="medium",
            search_hints=["[industry] digital talent gap", "transformation organizational design"],
        ),
        ResearchQuestion(
            question="What is the typical investment and timeline for comparable transformations?",
            branch="roadmap",
            data_type="financial",
            priority="high",
            search_hints=["digital transformation cost benchmark", "transformation program timeline"],
        ),
    ],

    stage1_fields=["transformation_trigger", "current_maturity_estimate"],

    stage2_additions="""
<template_guidance>
This is a TRANSFORMATION engagement. The MECE structure must paint a clear from→to picture:
1. Where is change creating value? (quantify the opportunity — not just "digital is important")
2. What is the maturity gap? (specific, scored — current vs. target vs. industry leaders)
3. What is the roadmap? (phased, with investment, quick wins in first 90 days)

Avoid generic transformation platitudes. Every claim needs a benchmark or case study reference.
The hypothesis should state the specific transformation target with timeline and investment.
</template_guidance>""",

    stage3_additions="""
<template_slide_rules>
Transformation deck structure:
1. Title slide
2. Executive Summary (transformation vision + investment ask)
3. Agenda
4-5. Value Opportunity: Where change creates impact (sizing charts)
6-7. Current State Assessment: Maturity gap analysis (harvey_balls or radar)
8-9. Target Operating Model: Future state vision (framework diagram)
10-12. Transformation Roadmap: Phases, milestones, quick wins (timeline)
13. Investment Case: Costs vs. returns over 3-5 years (waterfall or line)
14. Change Management: People and organization plan
15. Risks & Mitigants
16. Recommendations & Next Steps

MUST include: maturity assessment (harvey_balls), roadmap timeline, investment waterfall.
</template_slide_rules>""",
)

# ─────────────────────────────────────────────────────────────
# Template 5: Market Entry / Growth Strategy
# ─────────────────────────────────────────────────────────────

MARKET_ENTRY = EngagementTemplate(
    id="market_entry",
    name="Market Entry / Growth Strategy",
    description="Size the market, analyze competition, design go-to-market strategy, and build the business case",
    icon="Rocket",
    default_audience="board",
    deck_type="market_entry",
    slide_range=(14, 20),
    default_output_formats=["strategy_deck", "executive_memo", "one_pager"],
    default_research_depth="comprehensive",
    frameworks=["tam_sam_som", "porter_five_forces", "go_to_market", "scenario_planning"],
    recommended_domains=["worldbank.org", "statista.com", "euromonitor.com", "mckinsey.com"],

    mece_branches=[
        {
            "question": "Is the target market large enough and growing?",
            "evidence_needed": "TAM/SAM/SOM, growth forecast, demand drivers, regulatory environment",
            "so_what_template": "The [market] TAM is $[X]B with SAM of $[Y]B, growing at [Z]% driven by [drivers]",
        },
        {
            "question": "Can we build a competitive position and win share?",
            "evidence_needed": "Competitive map, entry barriers, differentiation options, local partner landscape",
            "so_what_template": "Entry is feasible via [strategy] leveraging [advantage], targeting [X]% share in [Y] years",
        },
        {
            "question": "Does the business case justify the investment?",
            "evidence_needed": "Revenue projections, cost structure, required investment, break-even timeline",
            "so_what_template": "Investment of $[X]M breaks even in [Y] years with NPV of $[Z]M under base case",
        },
    ],

    research_checklist=[
        ResearchQuestion(
            question="What is the total addressable market (TAM) and serviceable market (SAM)?",
            branch="market_attractiveness",
            data_type="market_size",
            priority="high",
            search_hints=["[market] [region] market size", "[market] TAM SAM SOM", "[market] [country] forecast"],
        ),
        ResearchQuestion(
            question="What is the regulatory and trade environment?",
            branch="market_attractiveness",
            data_type="regulatory",
            priority="high",
            search_hints=["[country] [industry] regulation", "[country] foreign investment rules", "[country] trade barriers"],
        ),
        ResearchQuestion(
            question="Who are the dominant players and what is their market share?",
            branch="competitive_position",
            data_type="benchmark",
            priority="high",
            search_hints=["[market] [region] market share", "[market] [country] competitors", "[market] competitive landscape"],
        ),
        ResearchQuestion(
            question="What entry barriers exist and how have others overcome them?",
            branch="competitive_position",
            data_type="case_study",
            priority="medium",
            search_hints=["[market] [country] entry barriers", "[market] market entry case study"],
        ),
        ResearchQuestion(
            question="What go-to-market models work in this region/segment?",
            branch="competitive_position",
            data_type="case_study",
            priority="medium",
            search_hints=["[market] [region] go-to-market strategy", "[market] distribution channels [country]"],
        ),
        ResearchQuestion(
            question="What are potential local partners or acquisition targets?",
            branch="competitive_position",
            data_type="benchmark",
            priority="medium",
            search_hints=["[market] [country] potential partners", "[market] [country] companies list"],
        ),
        ResearchQuestion(
            question="What is the typical cost structure and required investment for market entry?",
            branch="business_case",
            data_type="financial",
            priority="high",
            search_hints=["[market] [country] entry cost", "[market] startup costs [region]", "[market] investment required"],
        ),
    ],

    stage1_fields=["target_market_region", "entry_mode_preference"],

    stage2_additions="""
<template_guidance>
This is a MARKET ENTRY / GROWTH STRATEGY. The MECE structure must be investable:
1. Market attractiveness (TAM/SAM/SOM — must be quantified, not estimated)
2. Competitive position (barriers, players, differentiation — specific names and numbers)
3. Business case (investment, revenue build, break-even — scenario-based)

Include both base case and downside scenario. Every market size figure needs a source.
The hypothesis should state the recommended entry mode, target market, and investment range.
</template_guidance>""",

    stage3_additions="""
<template_slide_rules>
Market Entry / Growth Strategy deck structure:
1. Title slide
2. Executive Summary (entry recommendation + investment range)
3. Agenda
4-5. Market Opportunity: TAM/SAM/SOM sizing + growth (bar chart + line)
6. Regulatory Environment: Key enablers and barriers
7-8. Competitive Landscape: Player map + market share (bar chart + matrix_2x2)
9. Entry Strategy: Recommended mode (organic/acquisition/JV/partnership)
10-11. Go-to-Market Plan: Phased approach with milestones
12-13. Financial Case: Revenue build, investment, break-even (waterfall + scenarios)
14. Key Risks & Mitigants
15. Recommendations & Decision Ask
16. Next Steps (market validation activities)

MUST include: TAM/SAM/SOM bar chart, competitive positioning matrix, financial waterfall, scenario comparison.
</template_slide_rules>""",
)


# ─────────────────────────────────────────────────────────────
# Template Registry
# ─────────────────────────────────────────────────────────────

_TEMPLATES: dict[str, EngagementTemplate] = {
    t.id: t for t in [
        STRATEGIC_ASSESSMENT,
        COMMERCIAL_DUE_DILIGENCE,
        PERFORMANCE_IMPROVEMENT,
        TRANSFORMATION,
        MARKET_ENTRY,
    ]
}


def get_template(template_id: str) -> EngagementTemplate | None:
    """Get a template by ID. Returns None if not found."""
    return _TEMPLATES.get(template_id)


def list_templates() -> list[EngagementTemplate]:
    """List all available engagement templates."""
    return list(_TEMPLATES.values())


def get_template_ids() -> list[str]:
    """Get all template IDs."""
    return list(_TEMPLATES.keys())
