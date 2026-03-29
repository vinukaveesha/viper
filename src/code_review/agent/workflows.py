"""ADK workflow prototypes for review execution."""

from __future__ import annotations

from code_review.agent.agent import create_review_agent
from code_review.providers.base import ProviderInterface


def _per_file_instruction_suffix(file_path: str, head_sha: str) -> str:
    """File-specific instruction appended to each workflow sub-agent."""
    head_sha_clause = f" head_sha={head_sha}." if head_sha else ""
    ref_guidance = (
        f' When calling get_file_lines for surrounding context, use ref="{head_sha}" exactly.'
        if head_sha
        else ""
    )
    return (
        "Review exactly one file from this PR. "
        f'Use path "{file_path}" in every finding.'
        + head_sha_clause
        + " Call get_pr_diff_for_file with that exact file path to fetch the diff for this file."
        + " Use the <L{n}> annotation value as the line field in each finding."
        + ref_guidance
        + ' Output a JSON object of the form {"findings": [...]} for this file only.'
        + ' If there are no issues in this file, output exactly {"findings": []}.'
    )


def create_sequential_file_review_agent(
    provider: ProviderInterface,
    review_standards: str,
    paths: list[str],
    *,
    head_sha: str = "",
    context_brief_attached: bool = False,
):
    """Build a narrow SequentialAgent prototype for tool-based per-file review."""
    from google.adk.agents import SequentialAgent

    sub_agents = []
    for index, path in enumerate(paths):
        agent = create_review_agent(
            provider,
            review_standards,
            findings_only=True,
            disable_tools=False,
            context_brief_attached=context_brief_attached,
        )
        agent.name = f"file_review_{index}"
        agent.instruction = agent.instruction.rstrip() + "\n\n" + _per_file_instruction_suffix(
            path, head_sha
        )
        sub_agents.append(agent)

    return SequentialAgent(
        name="sequential_file_review_agent",
        description="Phase 3 prototype: review a prepared file list sequentially.",
        sub_agents=sub_agents,
    )
