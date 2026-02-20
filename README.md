# Code Review Agent

AI-driven code review agent for CI/CD pipelines. Reviews pull request diffs, posts inline comments, and tracks resolved issues. Supports Gitea (with extensibility for GitLab, Bitbucket) and configurable LLMs (Gemini, OpenAI, Ollama).

## Quick Start

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS; on Windows: .venv\Scripts\activate

# Install
pip install -e .

# Run (requires SCM_* and LLM env vars)
code-review review --provider gitea --owner myorg --repo myrepo --pr 42
```

## Configuration

Copy `.env.example` to `.env` and set:

- `SCM_PROVIDER`, `SCM_URL`, `SCM_TOKEN` — SCM access
- `LLM_PROVIDER`, `LLM_MODEL` — LLM (gemini, openai, anthropic, ollama)

## Development

```bash
source .venv/bin/activate   # Use project venv
pip install -e ".[dev]"
pytest
```
