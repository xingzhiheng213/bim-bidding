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
