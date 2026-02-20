"""Tests for repo content safety (truncation, delimiter)."""

from code_review.providers.safety import TRUNCATE_SUFFIX, truncate_repo_content


def test_truncate_repo_content_under_limit():
    content = "line1\nline2"
    assert truncate_repo_content(content, max_bytes=100) == content


def test_truncate_repo_content_over_limit():
    content = "a" * (20 * 1024)
    result = truncate_repo_content(content, max_bytes=16 * 1024)
    assert result.endswith(TRUNCATE_SUFFIX)
    assert len(result.encode("utf-8")) <= 16 * 1024 + len(TRUNCATE_SUFFIX.encode("utf-8"))


def test_truncate_repo_content_utf8_boundary():
    # Multi-byte chars: 3 bytes each, so 5 chars = 15 bytes
    content = "\u00e9" * 6000  # 18000 bytes
    result = truncate_repo_content(content, max_bytes=100)
    assert result.endswith(TRUNCATE_SUFFIX)
    assert len(result.encode("utf-8")) <= 100 + len(TRUNCATE_SUFFIX.encode("utf-8"))
