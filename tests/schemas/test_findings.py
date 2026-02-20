"""Tests for FindingV1 schema."""

import pytest

from code_review.schemas.findings import FindingV1


def test_finding_v1_minimal():
    f = FindingV1(
        path="a.py",
        line=10,
        severity="suggestion",
        code="unused-var",
        message="Remove unused variable.",
    )
    assert f.version == "1"
    assert f.path == "a.py"
    assert f.line == 10
    assert f.get_body() == "Remove unused variable."
    assert f.body is None


def test_finding_v1_with_body():
    f = FindingV1(
        path="b.py",
        line=1,
        severity="critical",
        code="sql-injection",
        message="Default message",
        body="Custom body text",
    )
    assert f.get_body() == "Custom body text"


def test_finding_v1_optional_fields():
    f = FindingV1(
        path="c.py",
        line=5,
        end_line=7,
        severity="info",
        code="style",
        message="Prefer X.",
        category="Style",
        fingerprint_hint="some_identifier",
    )
    assert f.end_line == 7
    assert f.category == "Style"
    assert f.fingerprint_hint == "some_identifier"


def test_finding_v1_line_ge_1():
    with pytest.raises(ValueError):
        FindingV1(
            path="x",
            line=0,
            severity="info",
            code="x",
            message="x",
        )
