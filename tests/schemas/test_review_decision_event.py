"""Tests for ReviewDecisionEventContext and env loading."""

import os
from unittest.mock import patch

from code_review.schemas.review_decision_event import (
    ReviewDecisionEventContext,
    event_allows_decision_only_skip_when_bot_not_blocking,
    review_decision_event_context_from_env,
)

_EVENT_ENV_KEYS = (
    "CODE_REVIEW_EVENT_COMMENT_ID",
    "CODE_REVIEW_EVENT_THREAD_ID",
    "CODE_REVIEW_EVENT_ACTOR_LOGIN",
    "CODE_REVIEW_EVENT_ACTOR_ID",
    "CODE_REVIEW_EVENT_SOURCE",
)


def test_context_normalizes_invalid_source():
    c = ReviewDecisionEventContext(source="nope")
    assert c.source == "full_review"


def test_context_accepts_valid_source():
    c = ReviewDecisionEventContext(comment_id="1", source="webhook_comment")
    assert c.source == "webhook_comment"


def test_context_normalizes_source_case_insensitive():
    c = ReviewDecisionEventContext(comment_id="1", source="WEBHOOK_COMMENT")
    assert c.source == "webhook_comment"


def test_has_audit_fields():
    assert not ReviewDecisionEventContext().has_audit_fields()
    assert ReviewDecisionEventContext(comment_id="1").has_audit_fields()


def test_from_env_returns_none_when_unset():
    with patch.dict(os.environ, dict.fromkeys(_EVENT_ENV_KEYS, ""), clear=False):
        assert review_decision_event_context_from_env() is None


def test_from_env_builds_context():
    with patch.dict(
        os.environ,
        {
            "CODE_REVIEW_EVENT_COMMENT_ID": "99",
            "CODE_REVIEW_EVENT_SOURCE": "webhook_comment",
        },
        clear=False,
    ):
        ctx = review_decision_event_context_from_env()
        assert ctx is not None
        assert ctx.comment_id == "99"


def test_extra_keys_ignored_on_model_validate():
    ctx = ReviewDecisionEventContext.model_validate(
        {"comment_id": "42", "unexpected": "ignored"}
    )
    assert ctx.comment_id == "42"


def test_event_allows_skip_only_when_comment_id_set():
    assert not event_allows_decision_only_skip_when_bot_not_blocking(None)
    assert not event_allows_decision_only_skip_when_bot_not_blocking(ReviewDecisionEventContext())
    assert not event_allows_decision_only_skip_when_bot_not_blocking(
        ReviewDecisionEventContext(actor_login="someone")
    )
    assert event_allows_decision_only_skip_when_bot_not_blocking(
        ReviewDecisionEventContext(comment_id="1")
    )
    assert event_allows_decision_only_skip_when_bot_not_blocking(
        ReviewDecisionEventContext(comment_id="42", actor_login="user")
    )
