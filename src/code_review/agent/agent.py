"""ADK agent definition for code review. Uses google.adk Agent (LlmAgent), tools, and generate_content_config."""

from __future__ import annotations

from typing import TYPE_CHECKING

from code_review.agent.tools.gitea_tools import create_findings_only_tools, create_gitea_tools
from code_review.config import get_llm_config
from code_review.models import get_configured_model
from code_review.providers.base import ProviderInterface

if TYPE_CHECKING:
    from google.adk.agents import Agent

# Instruction when agent posts comments itself (legacy)
BASE_INSTRUCTION = """
You are a code review agent. You will receive PR details (owner, repo, pr_number, head_sha).
Use get_pr_diff to fetch the diff, get_file_content for AGENTS.md/README/.cursor/rules context.
Call get_existing_review_comments to get the ignore list (manually resolved issues). Do not post comments for issues that match (path, body_hash) in the ignore list.
Analyze the diff for bugs, style, security, and best practices. Consider the language/framework.
Use post_review_comment for each finding: path, line, and body with [Critical]/[Suggestion]/[Info] prefix. Skip any finding that was manually resolved.
"""

# Instruction when agent returns findings only; runner filters and posts
FINDINGS_ONLY_INSTRUCTION = """
You are a code review agent. You will receive PR details (owner, repo, pr_number, head_sha).
Use get_pr_diff or get_pr_diff_for_file to fetch the diff. Use get_file_content for AGENTS.md/README. Use get_file_lines when you need surrounding context.
If language detection is ambiguous, call detect_language_context. Otherwise use the provided language/framework.
Your job is to find code issues only. Do NOT fetch existing comments or post comments. The orchestrator handles that.
Return your response as a JSON array of findings. Each finding must have: path (str), line (int), severity ("critical"|"suggestion"|"info"), code (str, e.g. unused-var), message (str). Optional: end_line, category, anchor, fingerprint_hint.
Format: [{"path":"...","line":N,"severity":"...","code":"...","message":"..."}, ...]
"""


def create_review_agent(
    provider: ProviderInterface,
    review_standards: str = "",
    findings_only: bool = True,
) -> Agent:
    """Create the code review LlmAgent. If findings_only=True, agent returns JSON findings; runner posts."""
    from google.adk.agents import Agent
    from google.genai import types

    llm_cfg = get_llm_config()
    generate_content_config = types.GenerateContentConfig(
        temperature=llm_cfg.temperature,
        max_output_tokens=llm_cfg.max_output_tokens,
    )

    if findings_only:
        tools = create_findings_only_tools(provider)
        instruction = FINDINGS_ONLY_INSTRUCTION
    else:
        tools = create_gitea_tools(provider)
        instruction = BASE_INSTRUCTION
    if review_standards:
        instruction = instruction.rstrip() + "\n\n" + review_standards

    return Agent(
        model=get_configured_model(),
        name="code_review_agent",
        instruction=instruction,
        tools=tools,
        generate_content_config=generate_content_config,
    )
