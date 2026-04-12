"""Pydantic schemas for Prompt Profile API (Phase B)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PromptProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=128)
    discipline: str = Field(..., min_length=1, max_length=32)
    semantic_overrides: dict[str, str] | None = None


class PromptProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=128)
    discipline: str | None = Field(default=None, min_length=1, max_length=32)
    semantic_overrides: dict[str, str] | None = None


class PromptProfileSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str | None
    discipline: str
    is_builtin: bool
    created_at: datetime
    updated_at: datetime


class PromptProfileDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str | None
    discipline: str
    is_builtin: bool
    semantic_overrides: dict | None
    user_id: str | None
    created_at: datetime
    updated_at: datetime


class GenerateSemanticRequest(BaseModel):
    """LLM: adapt built-in semantic prompt to profile name + discipline."""

    profile_name: str = Field(..., min_length=1, max_length=255)
    discipline: str = Field(..., min_length=1, max_length=32)
    slot_key: str | None = Field(
        default=None,
        description="Semantic slot to generate; omit or null for all slots.",
    )


class GenerateSemanticResponse(BaseModel):
    """Single-slot: slot_key + text. All slots: overrides only."""

    slot_key: str | None = None
    text: str | None = None
    overrides: dict[str, str] | None = None
