"""Tests that runner consults ignore list before posting (Phase 2)."""

from unittest.mock import MagicMock, patch

from code_review.providers.base import FileInfo


@patch("code_review.runner.get_context_window")
@patch("code_review.runner.get_provider")
@patch("code_review.runner.get_scm_config")
def test_ignore_list_consulted_before_posting(
    mock_get_scm_config, mock_get_provider, mock_get_context_window
):
    """Mock agent run: existing comment with same body hash as a finding; that finding is not posted."""
    from code_review.runner import run_review

    mock_get_scm_config.return_value = MagicMock(
        provider="gitea", url="https://x.com", token="x"
    )
    provider = MagicMock()
    provider.get_pr_files.return_value = [FileInfo(path="foo.py", status="modified")]
    provider.get_pr_diff.return_value = "diff"
    provider.get_file_content.return_value = "line1\nline2\nline3"
    # Existing comment body matches first finding
    provider.get_existing_review_comments.return_value = [
        MagicMock(
            path="foo.py",
            body="[Critical] Duplicate.",
            model_dump=lambda: {"path": "foo.py", "body": "[Critical] Duplicate."},
        )
    ]
    provider.post_review_comments = MagicMock()
    mock_get_provider.return_value = provider
    mock_get_context_window.return_value = 1_000_000

    findings_json = '''[
        {"path":"foo.py","line":1,"severity":"critical","code":"x","message":"Duplicate."},
        {"path":"foo.py","line":2,"severity":"suggestion","code":"y","message":"New."}
    ]'''
    mock_event = MagicMock()
    mock_event.is_final_response.return_value = True
    mock_event.content = MagicMock()
    mock_event.content.parts = [MagicMock(text=findings_json)]
    mock_runner_instance = MagicMock()
    mock_runner_instance.run.return_value = iter([mock_event])

    with patch("google.adk.runners.Runner", return_value=mock_runner_instance):
        to_post = run_review("o", "r", 1, head_sha="abc123", dry_run=False)

    assert len(to_post) == 1
    assert to_post[0].message == "New."
    provider.post_review_comments.assert_called_once()
    comments = provider.post_review_comments.call_args[0][3]
    assert len(comments) == 1
    assert "New." in comments[0][2]
