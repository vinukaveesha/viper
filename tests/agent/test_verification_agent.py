"""Tests for verification agent factory."""

from unittest.mock import MagicMock, patch

from code_review.agent.verification_agent import create_verification_agent


@patch("code_review.models.get_configured_verification_model")
@patch("code_review.config.get_llm_config")
@patch("google.adk.agents.Agent")
def test_create_verification_agent_uses_verification_model_helper(
    mock_agent_cls, mock_get_llm_cfg, mock_get_verification_model
):
    mock_get_llm_cfg.return_value = MagicMock(max_output_tokens=8192)
    mock_get_verification_model.return_value = "cheap-verification-model"
    inst = MagicMock()
    mock_agent_cls.return_value = inst

    out = create_verification_agent()

    assert out is inst
    _, kwargs = mock_agent_cls.call_args
    assert kwargs["model"] == "cheap-verification-model"
    assert kwargs["name"] == "verification_agent"
    mock_get_verification_model.assert_called_once()
