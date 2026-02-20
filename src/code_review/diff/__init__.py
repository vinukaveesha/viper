"""Diff parsing and comment positioning."""

from code_review.diff.fingerprint import build_fingerprint, content_hash, normalize_anchor
from code_review.diff.parser import DiffHunk, iter_new_lines, parse_unified_diff
from code_review.diff.position import CommentablePosition, get_commentable_positions, position_for_line

__all__ = [
    "build_fingerprint",
    "CommentablePosition",
    "content_hash",
    "DiffHunk",
    "get_commentable_positions",
    "iter_new_lines",
    "normalize_anchor",
    "parse_unified_diff",
    "position_for_line",
]
