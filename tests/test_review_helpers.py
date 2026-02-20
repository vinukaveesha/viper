"""Tests for review_helpers."""

from code_review.agent.tools.review_helpers import detect_language_context


def test_detect_language_context_paths_only():
    ctx = detect_language_context(["foo.py", "bar.py", "requirements.txt"])
    assert ctx["language"] == "python"
    assert ctx["confidence"] in ("high", "medium", "low")


def test_detect_language_context_with_sample():
    ctx = detect_language_context(
        ["requirements.txt", "src/main.py"],
        sample_content="fastapi>=0.100\ndjango>=4.0\n",
    )
    assert ctx["language"] == "python"
    assert ctx["framework"] == "fastapi" or ctx["framework"] == "django" or ctx["framework"] is None


def test_detect_language_context_empty():
    ctx = detect_language_context([])
    assert ctx["language"] == "unknown"
    assert ctx["framework"] is None
    assert ctx["confidence"] == "low"
