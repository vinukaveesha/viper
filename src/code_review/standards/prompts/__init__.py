"""Per-language review prompt fragments (runner-side)."""

from code_review.standards.prompts.base import BASE_REVIEW_PROMPT

# Per-language fragments - minimal for Phase 1; extend incrementally
_JS_TS_FRAGMENT = """
### JavaScript/TypeScript
- ESLint-style: null checks, async handling, no unused vars
- React/Vue/Node patterns if detected in imports
"""
_LANGUAGE_FRAGMENTS: dict[str, str] = {
    "python": """
### Python
- Follow PEP 8; consider type hints where appropriate
- Avoid mutable default args; handle exceptions explicitly
- Use async/await consistently; prefer context managers for resources
""",
    "javascript": _JS_TS_FRAGMENT,
    "typescript": _JS_TS_FRAGMENT,
    "go": """
### Go
- gofmt style; explicit error handling; defer/close for resources
- Concurrency patterns; exported vs unexported naming
""",
    "java": """
### Java
- Conventions; null safety; exception handling
- Spring/Jakarta patterns if detected in dependencies
""",
    "c": """
### C
- Memory safety: leaks, use-after-free, bounds; const correctness
- Header guards; static/linkage
""",
    "cpp": """
### C++
- Memory safety; RAII; const correctness
- Header guards; static/linkage; move semantics where appropriate
""",
}


def get_review_standards(language: str, framework: str | None) -> str:
    """
    Return combined prompt fragment for the given language and framework.
    Runner-side; not an agent tool.
    """
    parts = [BASE_REVIEW_PROMPT]
    lang_key = language.lower()
    if lang_key in _LANGUAGE_FRAGMENTS:
        parts.append(_LANGUAGE_FRAGMENTS[lang_key])
    if framework:
        parts.append(f"\n### Framework: {framework}\n")
    return "\n".join(parts)
