"""Provider-neutral webhook / CI context for review-decision-only runs (Phase C).

SCM-specific payload parsing should happen in CI or a thin adapter; the runner accepts
this normalized shape via :func:`review_decision_event_context_from_env` or programmatically.
"""

from __future__ import annotations

import os
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

ReviewDecisionEventSource = Literal[
    "full_review",
    "webhook_comment",
    "webhook_thread",
    "scheduled",
]

_VALID_SOURCES: frozenset[str] = frozenset(get_args(ReviewDecisionEventSource))

_ENV_FIELDS: tuple[tuple[str, str], ...] = (
    ("CODE_REVIEW_EVENT_COMMENT_ID", "comment_id"),
    ("CODE_REVIEW_EVENT_THREAD_ID", "thread_id"),
    ("CODE_REVIEW_EVENT_ACTOR_LOGIN", "actor_login"),
    ("CODE_REVIEW_EVENT_ACTOR_ID", "actor_id"),
    ("CODE_REVIEW_EVENT_SOURCE", "source"),
)


class ReviewDecisionEventContext(BaseModel):
    """Stable input surface for comment- or thread-driven review-decision recomputation."""

    model_config = ConfigDict(extra="ignore")

    comment_id: str = ""
    thread_id: str = ""
    actor_login: str = ""
    actor_id: str = ""
    source: ReviewDecisionEventSource = Field(
        default="full_review",
        description="How this run was triggered.",
    )

    @field_validator("source", mode="before")
    @classmethod
    def _normalize_source(cls, v: object) -> str:
        s = (str(v) if v is not None else "").strip() or "full_review"
        key = s.lower()
        return key if key in _VALID_SOURCES else "full_review"

    def has_audit_fields(self) -> bool:
        """True when any non-default identifying field is set (for structured logging)."""
        if self.source != "full_review":
            return True
        for value in (
            self.comment_id,
            self.thread_id,
            self.actor_login,
            self.actor_id,
        ):
            if value.strip():
                return True
        return False


def event_allows_decision_only_skip_when_bot_not_blocking(
    event: ReviewDecisionEventContext | None,
) -> bool:
    """True when opt-in may skip the gate if the provider reports *NOT_BLOCKING*.

    Default / empty event context never allows this (backward compatible: always recompute).
    Only reply events (comment_id present) are skippable; events without a comment id
    must still recompute so the bot can transition back to *APPROVE*.
    """
    if event is None or not event.has_audit_fields():
        return False
    return bool((event.comment_id or "").strip())


def review_decision_event_context_from_env() -> ReviewDecisionEventContext | None:
    """Build context from ``CODE_REVIEW_EVENT_*`` env vars; return None if all are empty."""
    values: dict[str, str] = {}
    any_set = False
    for env_key, field_name in _ENV_FIELDS:
        raw = (os.getenv(env_key) or "").strip()
        values[field_name] = raw
        if raw:
            any_set = True
    if not any_set:
        return None
    return ReviewDecisionEventContext.model_validate(values)
