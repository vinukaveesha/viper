"""Tests for diff position and fingerprint."""

from code_review.diff import (
    build_fingerprint,
    content_hash,
    get_commentable_positions,
    normalize_anchor,
    position_for_line,
)


def test_get_commentable_positions():
    diff = """diff --git a/foo.py b/foo.py
--- a/foo.py
+++ b/foo.py
@@ -1,2 +1,3 @@
 x
+y
 z
"""
    pos = get_commentable_positions(diff)
    assert len(pos) >= 1
    paths_lines = [(p.path, p.line_in_new_file) for p in pos]
    assert ("foo.py", 2) in paths_lines


def test_position_for_line():
    # Context lines in unified diff start with space
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,1 +1,2 @@\n a\n+b\n"
    p = position_for_line(diff, "a.py", 2)
    assert p is not None
    assert p.line_in_new_file == 2
    assert p.path == "a.py"
    assert position_for_line(diff, "a.py", 99) is None


def test_normalize_anchor():
    assert normalize_anchor("  foo  bar  ") == "foo bar"
    assert normalize_anchor("x\ty\nz") == "x y z"


def test_content_hash():
    h = content_hash("hello")
    assert len(h) == 16
    assert h == content_hash("hello")
    assert h != content_hash("world")


def test_build_fingerprint():
    fp = build_fingerprint("a.py", "abc123", "unused-var", "x = 1")
    assert len(fp) == 24
    assert fp == build_fingerprint("a.py", "abc123", "unused-var", "x = 1")
