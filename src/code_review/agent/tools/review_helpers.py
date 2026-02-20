"""Review helper tools: detect_language_context (LLM fallback for ambiguous detection).

get_review_standards is runner-side, not an agent tool — see code_review.standards.prompts.
"""

from code_review.standards import detect_from_paths, detect_from_paths_and_content


def detect_language_context(
    repo_paths: list[str], sample_content: str = ""
) -> dict[str, str | None]:
    """
    LLM fallback when deterministic detection is ambiguous.
    Uses path-based detection; sample_content can improve framework inference.

    Args:
        repo_paths: List of file paths in the repo/PR.
        sample_content: Optional content (e.g. from package.json, requirements.txt).

    Returns:
        Dict with language, framework, confidence. Framework may be None.
    """
    if not repo_paths:
        return {"language": "unknown", "framework": None, "confidence": "low"}
    content_by_path: dict[str, str] = {}
    if sample_content:
        # If caller provides sample, associate with first matching path
        for p in repo_paths[:5]:
            content_by_path[p] = sample_content
    detected = (
        detect_from_paths_and_content(repo_paths, content_by_path)
        if content_by_path
        else detect_from_paths(repo_paths)
    )
    return {
        "language": detected.language,
        "framework": detected.framework,
        "confidence": detected.confidence,
    }
