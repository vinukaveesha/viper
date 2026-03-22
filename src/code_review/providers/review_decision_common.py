"""Shared helpers for SCM review decision submission (approve / request changes)."""

from __future__ import annotations

from typing import Any

DEFAULT_AUTOMATED_REVIEW_BODY = "Automated review decision by Viper."


def effective_review_body(body: str, *, default: str | None = None) -> str:
    """Return stripped ``body`` or the default automated-review sentence."""
    t = (body or "").strip()
    if t:
        return t
    d = default if default is not None else DEFAULT_AUTOMATED_REVIEW_BODY
    return d


def github_style_pull_review_json(decision: str, body: str, head_sha: str) -> dict[str, Any]:
    """Build JSON body for GitHub- and Gitea-compatible ``POST .../pulls/:id/reviews``."""
    payload: dict[str, Any] = {
        "event": decision,
        "body": effective_review_body(body),
    }
    if head_sha:
        payload["commit_id"] = head_sha
    return payload


def gitlab_note_with_submit_review_requested_changes(body: str) -> str:
    """MR note text that runs GitLab quick action ``/submit_review requested_changes``."""
    text = effective_review_body(body)
    return f"{text}\n\n/submit_review requested_changes"
