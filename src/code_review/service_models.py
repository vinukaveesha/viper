"""Shared models for thin webhook-driven edge services."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from code_review.schemas.review_decision_event import ReviewDecisionEventContext


class ServiceReviewJob(BaseModel):
    """Provider-neutral job payload for edge services invoking the Viper runner."""

    model_config = ConfigDict(extra="ignore")

    owner: str
    repo: str
    pr_number: int = Field(..., ge=1)
    head_sha: str = ""
    base_sha: str = ""
    review_decision_only: bool = False
    event_name: str = ""
    action: str = ""
    event_context: ReviewDecisionEventContext | None = None
