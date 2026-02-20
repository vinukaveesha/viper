"""Language/framework detection and review standards."""

from code_review.standards.detector import DetectedContext, detect_from_paths, detect_from_paths_and_content
from code_review.standards.prompts import get_review_standards

__all__ = [
    "DetectedContext",
    "detect_from_paths",
    "detect_from_paths_and_content",
    "get_review_standards",
]
