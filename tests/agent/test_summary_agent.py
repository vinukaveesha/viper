import pytest
from unittest.mock import MagicMock, patch
from code_review.agent.summary_agent import generate_pr_summary
from code_review.schemas.findings import FindingV1

def test_generate_pr_summary_incremental_prompt():
    agent = MagicMock()
    pr_info = MagicMock()
    pr_info.title = "Test PR"
    pr_info.description = "Test Desc"
    # Ensure FindingV1 has all required fields for validation if needed,
    # though here we are just passing a list of them.
    findings = [
        FindingV1(path="file.py", line=10, message="Issue", severity="high", code="test-code")
    ]
    changed_paths = ["file.py"]
    
    # Patch the helper in orchestration instead of local import
    with patch("code_review.orchestration.runner_utils._run_agent_and_collect_response") as mock_run:
        mock_run.return_value = "Summary Text"
        
        generate_pr_summary(
            agent, 
            pr_info, 
            findings, 
            changed_paths, 
            incremental_base_sha="abcdef1234567890",
            incremental_commits=["Fixed bug A", "Added feature B"]
        )
        
        # Check the prompt
        args, _ = mock_run.call_args
        content = args[2]
        prompt = content.parts[0].text
        
        print(f"PROMPT:\n{prompt}")
        
        assert "Incremental Review Context: from abcdef123456" in prompt
        assert "Incremental commits in this update:" in prompt
        assert "- Fixed bug A" in prompt
        assert "- Added feature B" in prompt
        assert "Changed Files: file.py" in prompt

def test_generate_pr_summary_non_incremental_prompt():
    agent = MagicMock()
    pr_info = MagicMock()
    pr_info.title = "Test PR"
    pr_info.description = "Test Desc"
    findings = []
    changed_paths = ["file.py"]
    
    with patch("code_review.orchestration.runner_utils._run_agent_and_collect_response") as mock_run:
        mock_run.return_value = "Summary Text"
        
        generate_pr_summary(
            agent, 
            pr_info, 
            findings, 
            changed_paths
        )
        
        # Check the prompt
        args, _ = mock_run.call_args
        content = args[2]
        prompt = content.parts[0].text
        
        assert "Incremental Review Context" not in prompt
        assert "Changed Files: file.py" in prompt
