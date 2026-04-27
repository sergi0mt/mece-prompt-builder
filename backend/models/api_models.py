"""Pydantic request/response schemas for the API."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Projects ──

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    audience: str = "client"
    deck_type: str = "strategic"
    engagement_type: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    audience: Optional[str] = None
    deck_type: Optional[str] = None
    engagement_type: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    audience: str
    deck_type: str
    engagement_type: Optional[str] = None
    created_at: str
    updated_at: str
    upload_count: int = 0
    slide_count: int = 0
    current_stage: int = 0


# ── Uploads ──

class UploadResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_size: Optional[int]
    content_type: Optional[str]
    has_extracted_text: bool = False
    created_at: str


# ── Sessions ──

class SessionResponse(BaseModel):
    id: str
    project_id: str
    current_stage: int
    stage_data: dict = {}
    created_at: str


# ── Messages ──

class MessageCreate(BaseModel):
    content: str
    use_web_search: bool = False
    research_depth: str = "standard"  # "quick" | "standard" | "detailed" | "comprehensive"
    auto_refine: bool = False  # Enable self-refine loop after slide generation
    output_tone: str = "professional"  # "professional" | "executive" | "technical" | "persuasive"
    output_audience: str = ""  # Override audience for output style (empty = use project default)
    output_language: str = ""  # Force output language (empty = auto-detect)


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    stage: Optional[int]
    metadata: dict = {}
    created_at: str


# ── Slides ──

class SlideUpdate(BaseModel):
    action_title: Optional[str] = None
    content_json: Optional[dict] = None
    slide_type: Optional[str] = None


class SlideResponse(BaseModel):
    id: str
    project_id: str
    position: int
    slide_type: str
    action_title: str
    content_json: dict = {}
    is_appendix: bool = False
    preview_image: Optional[str] = None
    created_at: str


class SlideReorderRequest(BaseModel):
    slide_ids: list[str]


# ── Decks ──

class DeckResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    validation_score: Optional[int]
    validation_report: Optional[dict]
    generated_at: str


# ── Validation ──

class ValidationResponse(BaseModel):
    score: int
    passed: bool
    errors: list[dict] = []
    warnings: list[dict] = []
    summary: str


# -- Engagement Templates --

class EngagementTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    default_audience: str
    default_output_formats: list[str]
    research_question_count: int
    mece_branch_count: int
    slide_range_min: int
    slide_range_max: int
