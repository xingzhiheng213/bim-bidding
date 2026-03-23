"""Pydantic schemas for compare (diff) API."""
from typing import Literal

from pydantic import BaseModel


class CompareRequest(BaseModel):
    """Request body for POST /api/compare."""

    original: str = ""
    modified: str = ""


class DiffItem(BaseModel):
    """One segment of a structured diff (equal=unchanged, del=deleted, add=added)."""

    type: Literal["equal", "add", "del"]
    text: str


class CompareResponse(BaseModel):
    """Response for POST /api/compare."""

    diff: list[DiffItem]


class DiffResponse(BaseModel):
    """Response for GET .../steps/framework/diff and .../steps/chapters/diff."""

    original: str
    modified: str
    diff: list[DiffItem]


class FrameworkCompareMeta(BaseModel):
    """Metadata for framework diff availability."""

    has_diff: bool


class ChapterCompareMetaItem(BaseModel):
    """One chapter entry in compare meta."""

    number: int
    has_diff: bool
    label: str


class CompareMetaResponse(BaseModel):
    """Task-level compare metadata: which items have before/after versions."""

    has_any: bool
    framework: FrameworkCompareMeta
    chapters: list[ChapterCompareMetaItem]
