"""Tests for review_decision_common helpers."""

from code_review.providers.review_decision_common import (
    DEFAULT_AUTOMATED_REVIEW_BODY,
    effective_review_body,
    github_style_pull_review_json,
    gitlab_note_with_submit_review_requested_changes,
)


def test_effective_review_body_uses_strip_and_default():
    assert effective_review_body("") == DEFAULT_AUTOMATED_REVIEW_BODY
    assert effective_review_body("  x  ") == "x"


def test_github_style_pull_review_json():
    j = github_style_pull_review_json("APPROVE", "hi", "abc")
    assert j == {"event": "APPROVE", "body": "hi", "commit_id": "abc"}
    j2 = github_style_pull_review_json("REQUEST_CHANGES", "", "")
    assert j2["event"] == "REQUEST_CHANGES"
    assert j2["body"] == DEFAULT_AUTOMATED_REVIEW_BODY
    assert "commit_id" not in j2


def test_gitlab_note_with_submit_review_requested_changes():
    note = gitlab_note_with_submit_review_requested_changes("Reason here")
    assert note.endswith("/submit_review requested_changes")
    assert "Reason here" in note
