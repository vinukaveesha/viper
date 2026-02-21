# Code Review Agent — Developer Guide

This guide explains the implementation of the AI-driven code review agent: architecture, data flow, key modules, configuration, and how to extend or test the system.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [End-to-End Flow](#4-end-to-end-flow)
5. [Key Modules](#5-key-modules)
6. [Configuration and Environment](#6-configuration-and-environment)
7. [Extension Points](#7-extension-points)
8. [Testing](#8-testing)
9. [References](#9-references)

---

## 1. Overview

The code review agent:

- **Input**: A pull request (owner, repo, PR number, optional head SHA).
- **Process**: Fetches the PR diff and context via an SCM provider, runs a Google ADK agent (LLM + tools) to produce structured findings, then filters and posts inline comments (and optionally a PR summary) via the same provider.
- **Output**: Inline review comments on the PR; programmatic callers receive a list of `FindingV1` that were (or would be) posted.

Design principles:

- **Findings-only agent**: The LLM agent only discovers issues and returns a JSON array of findings. The **runner** (Python) handles fetching existing comments, building an ignore set, fingerprinting, idempotency, and posting. This keeps the agent focused and avoids giving the LLM access to “post” or “resolve” tools in the default mode.
- **Provider-agnostic**: SCM access is behind `ProviderInterface`; concrete implementations exist for Gitea, GitHub, GitLab, and Bitbucket.
- **LLM-agnostic**: The model is chosen via config (Gemini, OpenAI, Anthropic, Ollama, Vertex); the agent uses Google ADK’s `Agent` and model factory.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CLI (__main__.py)                                                       │
│  code-review review --owner X --repo Y --pr N [--head-sha SHA]           │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Runner (runner.py)                                                      │
│  • Load config (SCM + LLM)                                              │
│  • get_provider() → ProviderInterface                                   │
│  • Skip review? (label / title pattern)                                  │
│  • Fetch existing comments → build ignore set                           │
│  • Idempotency check (run id in comment markers)                        │
│  • get_pr_files → detect language → get_review_standards                 │
│  • create_review_agent(provider, review_standards, findings_only=True)  │
│  • ADK Runner + InMemorySessionService                                  │
│  • If diff too large: loop per file; else single run                    │
│  • runner.run() → collect response text → _findings_from_response()      │
│  • Filter findings (ignore set, fingerprint)                            │
│  • Format bodies, add fingerprint marker → post_review_comments         │
│  • post_pr_summary_comment (then observability.finish_run)              │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌──────────────────┐    ┌────────────────────────────┐   ┌─────────────────┐
│  Provider        │    │  ADK Runner                 │   │  Observability  │
│  (Gitea/GitHub/  │    │  • Agent (model, tools,     │   │  start_run /    │
│   GitLab/        │    │    instruction)              │   │  finish_run    │
│   Bitbucket)     │    │  • Session                  │   │  (Prometheus /   │
│  get_pr_diff,    │    │  • run(user_id, session_id, │   │  OTel optional) │
│  get_pr_files,   │    │    new_message)              │   │                 │
│  post_review_    │    │  → LLM + tool calls          │   │                 │
│  comments, etc. │    │  → final response (JSON)     │   │                 │
└──────────────────┘    └────────────────────────────┘   └─────────────────┘
```

- **CLI** is the only user-facing entry point; it delegates to `run_review()`.
- **Runner** owns orchestration: config, provider, skip/idempotency, language detection, review standards, agent creation, ADK run(s), parsing, filtering, and posting.
- **Agent** is an ADK `Agent` (LlmAgent) with tools that call the **provider** (get diff, get file content, etc.). The agent does **not** call `post_review_comments` or `get_existing_review_comments` in findings-only mode.
- **Provider** is the only component that talks to the SCM API (HTTP). Observability is optional and used only inside the runner.

---

## 3. Project Structure

```
src/code_review/
├── __init__.py
├── __main__.py              # CLI: Typer app, review command → run_review()
├── config.py                 # SCMConfig, LLMConfig (Pydantic Settings); get_scm_config(), get_llm_config()
├── models.py                 # get_configured_model(), get_context_window(), get_max_output_tokens()
├── runner.py                 # run_review(); orchestration and ADK Runner
├── observability.py          # Optional Prometheus/OTel; start_run(), finish_run(), get_prometheus_registry()
├── agent/
│   ├── __init__.py           # create_review_agent
│   ├── agent.py              # create_review_agent(provider, review_standards, findings_only)
│   └── tools/
│       ├── __init__.py
│       ├── gitea_tools.py    # create_gitea_tools(), create_findings_only_tools() — wrap ProviderInterface
│       └── review_helpers.py # detect_language_context() — agent tool
├── providers/
│   ├── __init__.py           # get_provider(name, base_url, token); exports base types
│   ├── base.py               # ProviderInterface, InlineComment, ReviewComment, FileInfo, PRInfo, ProviderCapabilities
│   ├── safety.py             # truncate_repo_content()
│   ├── gitea.py              # GiteaProvider
│   ├── github.py             # GitHubProvider
│   ├── gitlab.py             # GitLabProvider
│   └── bitbucket.py          # BitbucketProvider
├── schemas/
│   └── findings.py          # FindingV1 (path, line, severity, code, message, ...)
├── diff/
│   ├── parser.py             # parse_unified_diff(), DiffHunk, iter_new_lines()
│   ├── position.py          # get_commentable_positions(), position_for_line(), CommentablePosition
│   └── fingerprint.py       # build_fingerprint(), surrounding_content_hash(), format_comment_body_with_marker(), parse_marker_from_comment_body()
├── standards/
│   ├── __init__.py           # detect_from_paths(), detect_from_paths_and_content(), get_review_standards()
│   ├── detector.py          # Language/framework from paths and optional content
│   └── prompts/
│       ├── base.py          # BASE_REVIEW_PROMPT
│       └── ...              # Per-language fragments (python, js, go, etc.)
└── formatters/
    └── comment.py           # finding_to_comment_body(f) → "[Severity] message"
```

---

## 4. End-to-End Flow

### 4.1 CLI to Runner

1. User runs: `code-review review --owner myorg --repo myrepo --pr 42 --head-sha abc123` (or sets `SCM_OWNER`, `SCM_REPO`, `SCM_PR_NUM`, `SCM_HEAD_SHA`).
2. `__main__.py` resolves owner, repo, pr, head_sha from options or env; validates; calls `run_review(owner, repo, pr_number, head_sha, dry_run=..., print_findings=...)`.

### 4.2 Runner Steps (summary)

| Step | What happens |
|------|-------------------------------|
| 1 | Generate `trace_id`; call `observability.start_run(trace_id)`. |
| 2 | Load `get_scm_config()`, `get_llm_config()`; instantiate `get_provider(cfg.provider, cfg.url, cfg.token)`. |
| 3 | **Skip review**: `provider.get_pr_info(owner, repo, pr_number)`; if skip label or title pattern matches → log, `finish_run`, return `[]`. |
| 4 | **Existing comments**: `provider.get_existing_review_comments(...)`; build `ignore_set` with `_build_ignore_set()` (path + body hash, path + fingerprint from marker). |
| 5 | **Idempotency**: If `head_sha` is set, build `run_id` from provider/owner/repo/pr/head_sha/agent_version/config_hash. If any existing comment body contains this run id in the marker → skip run, return `[]`. |
| 6 | **PR files**: `provider.get_pr_files(owner, repo, pr_number)` → list of paths. |
| 7 | **Language & standards**: `detect_from_paths(paths)` → `DetectedContext`; `get_review_standards(language, framework)` → string appended to agent instruction. |
| 8 | **Agent**: `create_review_agent(provider, review_standards, findings_only=True)` → ADK `Agent` with model, instruction, tools, `generate_content_config`. |
| 9 | **Session**: `InMemorySessionService()`; create session with `app_name`, `user_id`, `session_id`. |
| 10 | **Runner**: `Runner(agent=agent, app_name=..., session_service=...)`. |
| 11 | **Token budget**: `diff_budget = get_context_window() * DIFF_TOKEN_BUDGET_RATIO`; `full_diff = provider.get_pr_diff(...)`; if `_estimate_tokens(full_diff) > diff_budget` and there are paths → **file-by-file**: for each path, build user message “Review this PR … Review only this file: {path}”, call `runner.run(..., new_message=content)`, collect response, parse findings; else single message “Review this PR …”, one `runner.run()`, parse findings. |
| 12 | **Parse**: `_findings_from_response(response_text)` extracts JSON array and maps to `FindingV1` (invalid entries skipped). |
| 13 | **Filter**: For each finding, compute comment body and body hash; optionally `_fingerprint_for_finding()` using file lines at `head_sha`. Skip if `(path, body_hash)` or `(path, fingerprint)` in `ignore_set`; else append to `to_post`. |
| 14 | **Optional**: If `print_findings`, print each finding to stdout. |
| 15 | **Post** (if not dry_run and `to_post`): Require `head_sha`. For each finding, build `body` with `finding_to_comment_body()` and `format_comment_body_with_marker(fingerprint, version, run_id)`. Build list of `InlineComment`; call `provider.post_review_comments(...)`. On exception, fall back to posting one-by-one; on per-comment failure, post that finding as PR-level summary. Then `provider.post_pr_summary_comment(...)` with summary body. |
| 16 | **Finish**: `_log_run_complete(...)`; `observability.finish_run(run_handle, ...)`; return list of findings that were (or would be) posted. |

### 4.3 Where the LLM Is Used

All LLM calls occur inside **ADK’s `Runner.run()`**. The runner only:

- Builds the user message (PR context and optionally “Review only this file: path”).
- Calls `runner.run(user_id, session_id, new_message=content)`.
- Consumes the event stream and concatenates final response text.

The agent (inside ADK) uses `get_configured_model()` for the model and calls tools (e.g. `get_pr_diff`, `get_pr_diff_for_file`, `get_file_content`, `get_file_lines`, `get_pr_files`, `detect_language_context`), which in turn call the **provider**. So the provider is used both by the runner (get existing comments, get files, get diff, get file content for fingerprinting, post comments) and by the agent via tools (get diff, get file content, etc.).

---

## 5. Key Modules

### 5.1 `config.py`

- **SCMConfig**: `env_prefix="SCM_"`. Fields: `provider`, `url`, `token`, `owner`, `repo`, `pr_num`, `head_sha`, `base_sha`, `event`, `skip_label`, `skip_title_pattern`.
- **LLMConfig**: `env_prefix="LLM_"`. Fields: `provider`, `model`, `context_window`, `max_output_tokens`, `temperature`, `disable_tool_calls`, `timeout_seconds`, `max_retries`.
- **get_scm_config()**, **get_llm_config()**: Cached (lru_cache) so config is read once per process.

### 5.2 `models.py`

- **get_configured_model()**: Returns the ADK model: for `gemini`/`vertex` a string (e.g. `gemini-2.5-flash`); for `openai`/`anthropic`/`ollama` a `LiteLlm(model="provider/model")` instance. Uses `get_llm_config()`.
- **get_context_window()**, **get_max_output_tokens()**: Read from `LLMConfig`; used by runner (chunking) and by agent (via `generate_content_config` in `agent.py`).

### 5.3 `agent/agent.py`

- **create_review_agent(provider, review_standards="", findings_only=True)**:
  - If `findings_only`: tools from `create_findings_only_tools(provider)` (get_pr_diff, get_pr_diff_for_file, get_file_content, get_file_lines, get_pr_files, detect_language_context); instruction = `FINDINGS_ONLY_INSTRUCTION`.
  - Else: tools from `create_gitea_tools(provider)` (adds post_review_comment, get_existing_review_comments); instruction = `BASE_INSTRUCTION`.
  - Appends `review_standards` to instruction.
  - Builds `generate_content_config` from `get_llm_config()` (temperature, max_output_tokens).
  - Returns ADK `Agent(model=get_configured_model(), name="code_review_agent", instruction=..., tools=..., generate_content_config=...)`.

### 5.4 `agent/tools/gitea_tools.py`

- **create_gitea_tools(provider)** / **create_findings_only_tools(provider)**: Return lists of callables that close over `provider`. Each callable delegates to the corresponding `ProviderInterface` method (e.g. `get_pr_diff` → `provider.get_pr_diff(...)`). ADK treats these as function tools and wraps them automatically.
- **review_helpers.detect_language_context**: Agent tool that calls `detect_from_paths` / `detect_from_paths_and_content` from `standards` for ambiguous language detection.

### 5.5 `providers/`

- **base.py**: Defines `ProviderInterface` (ABC) and shared types: `InlineComment`, `ReviewComment`, `FileInfo`, `PRInfo`, `ProviderCapabilities`. All concrete providers implement the same interface.
- **get_provider(name, base_url, token)**: Returns `GiteaProvider` | `GitHubProvider` | `GitLabProvider` | `BitbucketProvider` for `name` in `gitea` | `github` | `gitlab` | `bitbucket`.
- **safety.py**: `truncate_repo_content(content, max_bytes)` used when feeding repo file content (e.g. README, AGENTS.md) to the agent to avoid unbounded context.

### 5.6 `schemas/findings.py`

- **FindingV1**: Pydantic model for one finding: `path`, `line`, `end_line`, `severity`, `code`, `message`, `body`, `category`, `anchor`, `fingerprint_hint`, `version`. Used to parse the agent’s JSON output and to represent “findings to post.” `get_body()` returns the comment text (body or message).

### 5.7 `diff/`

- **parser.py**: `parse_unified_diff(diff_text)` → list of `DiffHunk` (path, old/new start/count, lines). Used by providers for `get_pr_diff_for_file` and by position/fingerprint logic.
- **position.py**: `get_commentable_positions(hunks)` and `position_for_line()` map (path, line) to diff positions for provider-specific comment placement where needed.
- **fingerprint.py**: `surrounding_content_hash()`, `build_fingerprint()`, `format_comment_body_with_marker()`, `parse_marker_from_comment_body()`. The marker is a hidden HTML comment in each posted comment body (e.g. `<!-- code-review-agent:fingerprint=...;version=...;run=... -->`) for dedup and idempotency.

### 5.8 `standards/`

- **detector.py**: `detect_from_paths(paths)` and `detect_from_paths_and_content(paths, content_map)` return `DetectedContext` (language, framework, confidence). Used by runner and by the `detect_language_context` tool.
- **prompts/**: `get_review_standards(language, framework)` returns a string (base prompt + per-language fragment) appended to the agent instruction.

### 5.9 `formatters/comment.py`

- **finding_to_comment_body(f)**: Maps a `FindingV1` to the comment text shown in the PR (e.g. `[Critical]` / `[Suggestion]` / `[Info]` + message). Used when building bodies for posting and when computing body hashes for the ignore set.

### 5.10 `observability.py`

- Optional. When `CODE_REVIEW_METRICS=prometheus` (or similar) or `CODE_REVIEW_TRACING=otel` is set and optional deps are installed: **start_run(trace_id)**, **finish_run(run_handle, owner, repo, pr_number, files_count, findings_count, posts_count, duration_seconds)**. Can expose Prometheus metrics and/or OTel spans. Runner calls these at start and end of each run.

---

## 6. Configuration and Environment

Configuration is read via **Pydantic Settings** in `config.py`; no `.env` file is loaded by default (env vars must be set in the process or loaded by the caller).

### 6.1 SCM (`SCM_` prefix)

| Variable | Required | Description |
|----------|----------|-------------|
| `SCM_PROVIDER` | No (default: gitea) | `gitea` \| `github` \| `gitlab` \| `bitbucket` |
| `SCM_URL` | Yes | API base URL (e.g. `https://api.github.com`, `http://gitea:3000`) |
| `SCM_TOKEN` | Yes | API token for the SCM |
| `SCM_OWNER` | No | Repo owner (can be passed via CLI `--owner`) |
| `SCM_REPO` | No | Repo name (can be passed via CLI `--repo`) |
| `SCM_PR_NUM` | No | PR number (can be passed via CLI `--pr`) |
| `SCM_HEAD_SHA` | No | Head commit SHA (can be passed via CLI `--head-sha`); required when posting comments |
| `SCM_BASE_SHA` | No | Base commit SHA |
| `SCM_SKIP_LABEL` | No | If PR has this label, skip review (default `skip-review`; empty = disabled) |
| `SCM_SKIP_TITLE_PATTERN` | No | If PR title contains this, skip review (default `[skip-review]`) |

### 6.2 LLM (`LLM_` prefix)

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | No (default: gemini) | `gemini` \| `openai` \| `anthropic` \| `ollama` \| `vertex` |
| `LLM_MODEL` | No | Model name (e.g. `gemini-2.5-flash`) |
| `LLM_CONTEXT_WINDOW` | No | Context size in tokens (default 128000) |
| `LLM_MAX_OUTPUT_TOKENS` | No | Max output tokens (default 4096) |
| `LLM_TEMPERATURE` | No | 0 or low for deterministic review (default 0.0) |
| `LLM_DISABLE_TOOL_CALLS` | No | Debug: disable tool calls |
| `LLM_TIMEOUT_SECONDS` | No | Per-request timeout (default 60.0) |
| `LLM_MAX_RETRIES` | No | Max retries (default 3) |

Provider-specific keys (used by ADK/LiteLLM, not by `config.py`): `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`; for Ollama, `OLLAMA_API_BASE` (default `http://localhost:11434`).

### 6.3 Observability

- **Prometheus**: `CODE_REVIEW_METRICS=prometheus` or `CODE_REVIEW_PROMETHEUS=1`; optional deps: `pip install -e ".[observability]"`. Use `code_review.observability.get_prometheus_registry()` to expose `/metrics`.
- **OpenTelemetry**: `CODE_REVIEW_TRACING=otel` or `CODE_REVIEW_OTEL=1`; set `OTEL_EXPORTER_OTLP_ENDPOINT` or `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` for export.

---

## 7. Extension Points

### 7.1 Adding a New SCM Provider

1. Implement **ProviderInterface** in a new module under `providers/` (e.g. `providers/my_scm.py`). Implement: `get_pr_diff`, `get_pr_diff_for_file`, `get_file_content`, `get_file_lines`, `get_pr_files`, `post_review_comments`, `get_existing_review_comments`, `post_pr_summary_comment`, `get_pr_info`, `capabilities()`.
2. In `providers/__init__.py`, extend **get_provider(name, base_url, token)** to return your provider when `name == "my_scm"` and add it to `__all__`.
3. Extend **SCMConfig.provider** in `config.py` to include `"my_scm"` (e.g. `Literal[..., "my_scm"]`).
4. Add tests under `tests/providers/test_my_scm.py` with mocked HTTP.

### 7.2 Adding or Changing an LLM Backend

- **models.py**: In **get_configured_model()**, handle a new `LLMConfig.provider` value (e.g. another LiteLLM model string or a custom ADK model class). Ensure **get_context_window()** and **get_max_output_tokens()** remain consistent with config.
- **config.py**: Add the new provider to `LLMConfig.provider`’s `Literal` if needed.

### 7.3 Customizing the Agent (instruction / tools)

- **agent/agent.py**: Change **FINDINGS_ONLY_INSTRUCTION** or **BASE_INSTRUCTION**, or pass different `review_standards` from the runner. To add tools, extend **create_findings_only_tools** or **create_gitea_tools** in `agent/tools/gitea_tools.py` and ensure the agent receives them (and the instruction describes when to use them).

### 7.4 Customizing Review Criteria (language / framework)

- **standards/detector.py**: Extend path/config rules or confidence logic.
- **standards/prompts/**: Add or edit per-language fragments and wire them in **get_review_standards()** in `standards/` (e.g. in `prompts/__init__.py` or equivalent).

### 7.5 Comment Format and Fingerprinting

- **formatters/comment.py**: **finding_to_comment_body(f)** controls how each finding becomes comment text.
- **diff/fingerprint.py**: **format_comment_body_with_marker** and **parse_marker_from_comment_body** define the hidden marker format; **build_fingerprint** and **surrounding_content_hash** affect dedup and ignore list.

### 7.6 Programmatic Entry Point

- **run_review(owner, repo, pr_number, head_sha="", *, dry_run=False, print_findings=False)** in `runner.py`: Use this when integrating the agent from another service or script instead of the CLI. Returns `list[FindingV1]` (findings that were or would be posted).

---

## 8. Testing

### 8.1 Test Layout

Tests mirror the source layout and live under `tests/`:

- **cli/test_main.py**: CLI parsing, missing args, env fallback, `fail_on_critical`; mocks `run_review`.
- **test_runner.py**, **runner/test_*.py**: Runner and idempotency, chunking, observability; use a **MockProvider** (or similar) and **patch `google.adk.runners.Runner`** so `run()` yields a single final event with JSON findings (no real LLM).
- **test_providers_gitea.py**, **providers/test_github.py**, **providers/test_gitlab.py**, **providers/test_bitbucket.py**: Provider behavior with **mocked HTTP** (e.g. `@patch("code_review.providers.gitea.httpx.Client")` and set `request.return_value`).
- **tools/test_scm_tools.py**: Agent tools; **MagicMock** for the provider; call tool functions and assert delegation to the provider.
- **integration/test_gitea_agent_integration.py**: Runner + real GiteaProvider with **respx** for Gitea API; **Runner** patched so no real LLM; asserts POST to review endpoint with expected payload.
- **models/test_model_factory.py**: **patch get_llm_config**; assert `get_configured_model()`, `get_context_window()`, `get_max_output_tokens()` for different configs.
- **schemas/test_findings.py**, **standards/test_detector.py**, **standards/test_prompts.py**, **diff/test_*.py**, **formatters/test_comment_format.py**, **observability**: Unit tests for schemas, standards, diff, formatters, observability.
- **e2e/test_docker_gitea_e2e.py**: E2E placeholder; run with `RUN_E2E=1` when Gitea (and env) are available.
- **docker/test_dockerfile.py**: Dockerfile and compose sanity checks.

### 8.2 Mocking Patterns

- **Provider**: Implement a minimal `ProviderInterface` (or use `MagicMock(spec=ProviderInterface)`). In runner tests, **patch `code_review.runner.get_provider`** to return this provider.
- **ADK / LLM**: **Patch `google.adk.runners.Runner`** so the constructed runner’s **run()** returns an iterator yielding one (or more) events where `is_final_response()` is True and `content.parts[].text` is the JSON array of findings. No real Runner or model is invoked.
- **Config**: **Patch `get_scm_config`** and **get_llm_config** (and in runner tests **get_context_window**) so tests do not depend on real env.
- **HTTP (Gitea, etc.)**: Patch `httpx.Client` (or the client used by the provider) and set `.request.return_value` (or `.get`/`.post` if the provider uses them) to a mock response with `.text`, `.json()`, `.headers` as needed.

### 8.3 Running Tests

```bash
pip install -e ".[dev]"
pytest
# Exclude E2E (requires RUN_E2E=1 and live Gitea):
pytest --ignore=tests/e2e
```

---

## 9. References

- **README.md**: Quick start, configuration summary, Docker/CI, observability.
- **.env.example**: Example SCM and LLM env vars.
- **docs/IMPLEMENTATION_CHECKLIST.md**: Plan-derived checklist of implemented features.
- **docs/ADK_REVIEW.md**: How the implementation uses Google ADK (Agent, Runner, SessionService, tools, generate_content_config).
- **Google ADK**: [Agent Development Kit](https://google.github.io/adk-docs/) — LlmAgent, Runner, SessionService, function tools.
