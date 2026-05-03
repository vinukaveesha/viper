"""Tests for request-scoped service runtime helpers."""

from unittest.mock import patch

from pydantic import SecretStr

from code_review.config import CodeReviewAppConfig, SCMConfig
from code_review.service_models import ServiceReviewJob
from code_review.service_runtime import RequestScopedReviewRunner


def _base_scm_config() -> SCMConfig:
    return SCMConfig(
        provider="github",
        url="https://global.example/api",
        token=SecretStr("global-token"),
        bot_identity="global-bot",
    )


def test_request_scoped_runner_passes_explicit_configs_without_env_mutation():
    job = ServiceReviewJob(
        owner="acme",
        repo="demo",
        pr_number=7,
        head_sha="head123",
        base_sha="base456",
        review_decision_only=True,
    )
    runner = RequestScopedReviewRunner(
        scm_provider="github",
        scm_url="https://github.example/api/",
        dry_run=True,
    )

    with (
        patch("code_review.service_runtime.get_scm_config", return_value=_base_scm_config()),
        patch(
            "code_review.service_runtime.get_code_review_app_config",
            return_value=CodeReviewAppConfig(started_review_comment_posted=True),
        ),
        patch("code_review.service_runtime.run_review") as mock_run_review,
    ):
        runner.run_job(job, "job-token", bot_login="", started_review_notice_posted=False)

    mock_run_review.assert_called_once()
    kwargs = mock_run_review.call_args.kwargs
    scm_cfg = kwargs["scm_config"]
    app_cfg = kwargs["app_config"]
    assert kwargs["owner"] == "acme"
    assert kwargs["repo"] == "demo"
    assert kwargs["pr_number"] == 7
    assert kwargs["head_sha"] == "head123"
    assert kwargs["dry_run"] is True
    assert kwargs["review_decision"].only is True
    assert scm_cfg.provider == "github"
    assert scm_cfg.url == "https://github.example/api"
    assert scm_cfg.token.get_secret_value() == "job-token"
    assert scm_cfg.base_sha == "base456"
    assert scm_cfg.bot_identity == ""
    assert app_cfg.started_review_comment_posted is False


def test_request_scoped_runner_uses_job_bot_and_started_notice_flag():
    job = ServiceReviewJob(owner="acme", repo="demo", pr_number=7)
    runner = RequestScopedReviewRunner(
        scm_provider="gitlab",
        scm_url="https://gitlab.example/api",
    )

    with (
        patch("code_review.service_runtime.get_scm_config", return_value=_base_scm_config()),
        patch(
            "code_review.service_runtime.get_code_review_app_config",
            return_value=CodeReviewAppConfig(started_review_comment_posted=False),
        ),
        patch("code_review.service_runtime.run_review") as mock_run_review,
    ):
        runner.run_job(job, "job-token", bot_login=" viper-bot ", started_review_notice_posted=True)

    kwargs = mock_run_review.call_args.kwargs
    assert kwargs["scm_config"].bot_identity == "viper-bot"
    assert kwargs["app_config"].started_review_comment_posted is True
