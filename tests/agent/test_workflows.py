"""Tests for ADK workflow prototypes."""

from unittest.mock import MagicMock, patch

from code_review.agent.workflows import create_sequential_file_review_agent


@patch("google.adk.agents.SequentialAgent")
@patch("code_review.agent.workflows.create_review_agent")
def test_create_sequential_file_review_agent_builds_one_sub_agent_per_path(
    mock_create_review_agent, mock_sequential_agent_cls
) -> None:
    provider = MagicMock()
    sub_agent_a = MagicMock(name="sub_agent_a")
    sub_agent_a.instruction = "base instruction"
    sub_agent_b = MagicMock(name="sub_agent_b")
    sub_agent_b.instruction = "base instruction"
    mock_create_review_agent.side_effect = [sub_agent_a, sub_agent_b]
    sequential_instance = MagicMock()
    mock_sequential_agent_cls.return_value = sequential_instance

    result = create_sequential_file_review_agent(
        provider,
        "review standards",
        ["a.py", "b.py"],
        head_sha="sha1",
        context_brief_attached=True,
    )

    assert result is sequential_instance
    assert mock_create_review_agent.call_count == 2
    mock_create_review_agent.assert_any_call(
        provider,
        "review standards",
        findings_only=True,
        disable_tools=False,
        context_brief_attached=True,
    )
    _, kwargs = mock_sequential_agent_cls.call_args
    assert kwargs["name"] == "sequential_file_review_agent"
    assert len(kwargs["sub_agents"]) == 2
    assert kwargs["sub_agents"][0].name == "file_review_0"
    assert kwargs["sub_agents"][1].name == "file_review_1"
    assert 'Use path "a.py" in every finding.' in kwargs["sub_agents"][0].instruction
    assert 'Use path "b.py" in every finding.' in kwargs["sub_agents"][1].instruction
    assert 'use ref="sha1" exactly' in kwargs["sub_agents"][0].instruction
