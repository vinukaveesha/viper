"""Pydantic models for code review findings."""

from typing import Literal

from pydantic import BaseModel, Field


class FindingV1(BaseModel):
    """A single code review finding with position and metadata for fingerprinting."""

    path: str = Field(..., description="File path (relative to repo root)")
    line: int = Field(..., ge=1, description="Line number (or start line for ranges)")
    end_line: int | None = Field(default=None, ge=1, description="Optional end line for multi-line findings")
    severity: Literal["critical", "suggestion", "info"]
    code: str = Field(..., description="Issue code (e.g. unused-var) for fingerprinting")
    message: str = Field(..., description="Human-readable message body")
    anchor: str | None = Field(default=None, description="Optional anchor text for stable positioning when lines shift")
