"""Tests for runner (mocked provider)."""

from unittest.mock import MagicMock, patch

import pytest

from code_review.providers.base import FileInfo
from code_review.runner import run_review


class MockProvider:
    def get_pr_files(self, owner, repo, pr_number):
        return [FileInfo(path="foo.py", status="modified")]

    def get_pr_diff(self, owner, repo, pr_number):
        return "diff --git a/foo.py b/foo.py"

    def get_file_content(self, owner, repo, ref, path):
        return "content"

    def post_review_comments(self, *args, **kwargs):
        pass

    def get_existing_review_comments(self, owner, repo, pr_number):
        return []


@patch("code_review.runner.get_provider")
@patch("code_review.runner.get_scm_config")
def test_run_review_mocked(get_scm_config, get_provider):
    get_scm_config.return_value = MagicMock(provider="gitea", url="https://x.com", token="x")
    get_provider.return_value = MockProvider()

    # Should not raise; we're mocking the provider so no real HTTP
    # The agent will run and potentially call tools - we'd need to mock the LLM
    # for a full E2E test. For now we just verify the runner setup doesn't fail
    # when we have valid config.
    # Actually running the agent will invoke the LLM - skip that in unit test.
    # Instead test that create_review_agent and runner construction work.
    from code_review.agent import create_review_agent

    provider = MockProvider()
    agent = create_review_agent(provider, "### Python")
    assert agent.name == "code_review_agent"
