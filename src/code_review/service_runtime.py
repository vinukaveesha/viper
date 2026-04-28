"""Shared request-scoped runtime helpers for webhook edge services."""

from __future__ import annotations

import os
from contextlib import contextmanager
from threading import Lock
from typing import Iterator

from code_review.config import reset_config_cache
from code_review.runner import run_review
from code_review.service_models import ServiceReviewJob

_REVIEW_LOCK = Lock()


@contextmanager
def temporary_environment(overrides: dict[str, str]) -> Iterator[None]:
    """Temporarily apply environment overrides and reset cached config around the scope."""
    previous = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            os.environ[key] = value
        reset_config_cache()
        yield
    finally:
        for key, previous_value in previous.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
        reset_config_cache()


class RequestScopedReviewRunner:
    """Thin wrapper that invokes ``run_review`` with request-scoped SCM env overrides."""

    def __init__(self, *, scm_provider: str, scm_url: str, dry_run: bool = False) -> None:
        self.scm_provider = str(scm_provider or "").strip()
        self.scm_url = str(scm_url or "").strip().rstrip("/")
        self.dry_run = dry_run

    def _overrides_for_job(
        self,
        job: ServiceReviewJob,
        scm_token: str,
        *,
        bot_login: str = "",
        started_review_notice_posted: bool = False,
    ) -> dict[str, str]:
        overrides = {
            "SCM_PROVIDER": self.scm_provider,
            "SCM_URL": self.scm_url,
            "SCM_TOKEN": scm_token,
            "SCM_BASE_SHA": job.base_sha,
        }
        if bot_login:
            overrides["SCM_BOT_IDENTITY"] = bot_login
        if started_review_notice_posted:
            overrides["CODE_REVIEW_STARTED_REVIEW_COMMENT_POSTED"] = "true"
        return overrides

    def run_job(
        self,
        job: ServiceReviewJob,
        scm_token: str,
        bot_login: str = "",
        *,
        started_review_notice_posted: bool = False,
    ) -> None:
        """Execute one review job with request-scoped SCM credentials."""
        overrides = self._overrides_for_job(
            job,
            scm_token,
            bot_login=bot_login,
            started_review_notice_posted=started_review_notice_posted,
        )
        with _REVIEW_LOCK, temporary_environment(overrides):
            run_review(
                owner=job.owner,
                repo=job.repo,
                pr_number=job.pr_number,
                head_sha=job.head_sha,
                dry_run=self.dry_run,
                review_decision_only=job.review_decision_only,
                event_context=job.event_context,
            )
