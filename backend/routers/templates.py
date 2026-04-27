"""Engagement templates router."""
from fastapi import APIRouter, HTTPException
from ..models.api_models import EngagementTemplateResponse
from ..services.engagement_templates import get_template, list_templates

router = APIRouter(prefix="/templates", tags=["templates"])


def _to_response(t) -> EngagementTemplateResponse:
    """Convert an EngagementTemplate dataclass to the API response model."""
    return EngagementTemplateResponse(
        id=t.id,
        name=t.name,
        description=t.description,
        icon=t.icon,
        default_audience=t.default_audience,
        default_output_formats=t.default_output_formats,
        research_question_count=len(t.research_checklist),
        mece_branch_count=len(t.mece_branches),
        slide_range_min=t.slide_range[0],
        slide_range_max=t.slide_range[1],
    )


@router.get("")
async def get_templates() -> list[EngagementTemplateResponse]:
    """Return all available engagement templates."""
    return [_to_response(t) for t in list_templates()]


@router.get("/{template_id}")
async def get_template_detail(template_id: str) -> EngagementTemplateResponse:
    """Return detailed info for a single engagement template."""
    t = get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return _to_response(t)
