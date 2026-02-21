# Google ADK Usage Review

This document reviews the implementation against the plan’s requirement to **use Google ADK as much as possible** and notes alignments and optional follow-ups.

## What We Use from ADK

| ADK primitive | Usage | Location |
|---------------|--------|----------|
| **Agent (LlmAgent)** | `from google.adk.agents import Agent`; created with `model`, `name`, `instruction`, `tools`, `generate_content_config` | `agent/agent.py` |
| **Runner** | `from google.adk.runners import Runner`; `Runner(agent=agent, app_name=..., session_service=...)`; `runner.run(user_id, session_id, new_message=content)` | `runner.py` |
| **SessionService** | `from google.adk.sessions import InMemorySessionService`; `create_session_sync(app_name, user_id, session_id)` | `runner.py` |
| **FunctionTools** | Plain Python functions passed in `tools=[...]`; ADK wraps them as `FunctionTool` automatically (per ADK docs) | `agent/tools/gitea_tools.py` |
| **Model** | `get_configured_model()` returns model string (Gemini) or `LiteLlm(model="...")` for OpenAI/Anthropic/Ollama | `models.py` |
| **generate_content_config** | `types.GenerateContentConfig(temperature=..., max_output_tokens=...)` from config; passed to Agent for deterministic review | `agent/agent.py` |

## Plan Alignment

- **1.1 ADK overview**: We use Agent, Runner, SessionService, and function tools as the main building blocks. Orchestration (chunking, filtering, posting) is in the runner; the agent only does “find code issues” and returns findings.
- **1.2 Configurable LLM**: Model comes from config; Gemini via string, others via ADK’s `LiteLlm` in `models.py`. Temperature and max output tokens are applied via **generate_content_config** on the Agent (plan: “Deterministic temperature”, “LLM_MAX_OUTPUT_TOKENS”).
- **1.4 Tools**: Tools are ADK-compatible functions (docstrings, type hints); they wrap the provider and are passed as the agent’s `tools` list. Plan’s “not given to the agent” (e.g. `post_review_comments`, `get_existing_review_comments` in findings-only mode) is respected.
- **1.5 Agent definition**: Single root agent, findings-only instruction, tools list; no “god prompt”—deterministic logic (ignore list, fingerprinting, resolve/post) stays in the runner.

## Tool Binding (tool_context vs closure)

The plan says: *“Tool binding via tool_context is the idiomatic ADK way.”*

- **Current**: Provider is bound by **closure** in `create_gitea_tools(provider)` / `create_findings_only_tools(provider)`; each tool closes over `provider`.
- **ADK Python**: The function-tools docs show tools as plain functions with no `tool_context` parameter; “passing data between tools” uses session state (`temp:`). So in Python ADK, closure over the provider is a valid and common pattern.
- **Optional follow-up**: If we want tools to receive an invocation context (e.g. for auth/memory), we could introduce a first parameter that ADK injects (e.g. `InvocationContext` or similar) and read the provider from session state or context. Not required for current behavior.

## Session API (sync vs async)

- **Current**: `InMemorySessionService().create_session_sync(...)` and `runner.run(...)` (sync iterator).
- **ADK**: The sync session API is deprecated in favor of async (`create_session`, `runner.run_async`). Behavior is correct; for full alignment with ADK’s preferred API we could later switch to async session creation and `run_async` and make the entrypoint async (or run async from sync via `asyncio.run`).

## Summary

- **Agent**: ADK `Agent` (LlmAgent) with model, instruction, tools, and **generate_content_config** (temperature, max_output_tokens from config).
- **Runner**: ADK `Runner` + `InMemorySessionService`; single `runner.run(...)` per review (or per file when chunking).
- **Tools**: Plain functions; ADK wraps them as FunctionTools. Provider bound by closure; consistent with ADK Python examples.
- **Orchestration**: Runner handles token budget, file-by-file chunking, idempotency, ignore set, fingerprinting, and posting via the provider; the agent is used purely for “call tools and return findings.”

No custom agent or runner replacement is used; orchestration is implemented on top of ADK’s Runner and session APIs.
