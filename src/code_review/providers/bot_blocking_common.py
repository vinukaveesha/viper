"""Shared parsing for GitHub- / Gitea-style PR review lists (Phase D bot blocking)."""

from __future__ import annotations

import logging
from typing import Any

from code_review.providers.base import BotBlockingState

logger = logging.getLogger(__name__)


def _norm_review_state(raw: str) -> str:
    return raw.strip().upper().replace(" ", "_").replace("-", "_")


def blocking_state_from_github_style_reviews(
    reviews: list[Any],
    *,
    token_login_lower: str,
) -> BotBlockingState:
    """Use the latest review authored by *token_login_lower* on this PR/MR.

    GitHub uses ``CHANGES_REQUESTED``; Gitea may use ``REQUEST_CHANGES`` or similar.
    """
    mine: list[tuple[int, str]] = []
    for r in reviews:
        if not isinstance(r, dict):
            continue
        user = r.get("user")
        login = ""
        if isinstance(user, dict):
            login = str(user.get("login") or "").strip().lower()
        if not login or login != token_login_lower:
            continue
        rid = int(r.get("id") or 0)
        raw_state = str(r.get("state") or "")
        mine.append((rid, raw_state))
    if not mine:
        return "NOT_BLOCKING"
    mine.sort(key=lambda x: x[0])
    last_raw = mine[-1][1]
    norm = _norm_review_state(last_raw)
    if norm in (
        "CHANGES_REQUESTED",
        "REQUEST_CHANGES",
        "REQUESTED_CHANGES",
    ):
        return "BLOCKING"
    if norm == "APPROVED":
        return "NOT_BLOCKING"
    if norm in ("COMMENT", "COMMENTED", "DISMISSED", "PENDING", ""):
        return "NOT_BLOCKING"
    logger.debug("Unknown GitHub-style PR review state for token user: %r", last_raw)
    return "UNKNOWN"
