# Quick Start Guide

Get the code review agent running quickly: **Docker Compose** (recommended for local testing with Gitea + Jenkins) or **local install** (venv + CLI, e.g. against GitHub or a remote Gitea).

---

## Prerequisites

- **Docker** and **Docker Compose** (for the Docker Compose path)
- **Python 3.12+** (for the non-Docker path)
- **LLM API key** (e.g. `GOOGLE_API_KEY` for Gemini, or `OPENAI_API_KEY` for OpenAI)

---

## Option 1: Test with Docker Compose (recommended)

This brings up Gitea and Jenkins so you can run the agent from a CI pipeline or manually on the same network.

### 1. Start the stack

From the repository root:

```bash
docker compose up -d
```

- **Gitea**: http://localhost:3000  
- **Jenkins**: http://localhost:8080  

The agent is **not** a long-running service; you run it as a one-shot container (see below).

### 2. Configure Gitea

1. Open http://localhost:3000 and complete first-run setup (admin user, etc.).
2. Create a **repository** (e.g. `myrepo`) under a user or org (e.g. `myorg`).
3. Create an **API token**: **Settings → Applications → Generate New Token** (scope: read/write for the repo).
4. (Optional) For webhook-triggered pipelines: install a Gitea plugin in Jenkins and configure a webhook in Gitea to point to Jenkins (e.g. `http://jenkins:8080/gitea-webhook/post`). The webhook payload can be mapped to pipeline parameters (`SCM_OWNER`, `SCM_REPO`, `SCM_PR_NUM`, `SCM_HEAD_SHA`).

### 3. Configure Jenkins

1. Open http://localhost:8080. If setup wizard appears, complete it.
2. Add **credentials** so the pipeline can call Gitea and the LLM:
   - **SCM_TOKEN**: Secret text — your Gitea API token.
   - **GOOGLE_API_KEY** (or **OPENAI_API_KEY**, etc.): Secret text — your LLM API key.
3. Create a **Pipeline** job:
   - **Pipeline script from SCM** → point to this repo and set **Script Path** to `docker/jenkins/Jenkinsfile`,  
     **or** use **Pipeline script** and paste the contents of `docker/jenkins/Jenkinsfile`.
   - Ensure the job has access to the credentials (e.g. bind `SCM_TOKEN` and `GOOGLE_API_KEY` to env vars in the job config).

### 4. Build the agent image

From the repository root (so `docker/Dockerfile.agent` and `src/` are in context):

```bash
docker build -t code-review-agent -f docker/Dockerfile.agent .
```

### 5. Run a review

**Option A — From Jenkins (pipeline):**

- Run the pipeline with parameters: `SCM_OWNER`, `SCM_REPO`, `SCM_PR_NUM`, `SCM_HEAD_SHA` (and optionally `LLM_PROVIDER`, `LLM_MODEL`, `COMPOSE_PROJECT_NAME`).  
- The Jenkinsfile runs the agent container on the same Docker network as Gitea (`SCM_URL=http://gitea:3000`).

**Option B — Manual one-shot run:**

```bash
docker run --rm --network code-review_code-review-net \
  -e SCM_PROVIDER=gitea \
  -e SCM_URL=http://gitea:3000 \
  -e SCM_TOKEN=your_gitea_token \
  -e SCM_OWNER=myorg \
  -e SCM_REPO=myrepo \
  -e SCM_PR_NUM=1 \
  -e SCM_HEAD_SHA=abc123... \
  -e LLM_PROVIDER=gemini \
  -e LLM_MODEL=gemini-2.5-flash \
  -e GOOGLE_API_KEY=your_google_api_key \
  code-review-agent review --owner myorg --repo myrepo --pr 1 --head-sha abc123...
```

Replace `your_gitea_token`, `myorg`, `myrepo`, `1`, `abc123...`, and `your_google_api_key` with real values. Get the head SHA from the PR’s latest commit (e.g. from Gitea’s PR page).

### Custom Compose project name

If you start Compose with a different project name (e.g. `docker compose -p myproject up`), the Docker network name changes (e.g. `myproject_code-review-net`). Set **COMPOSE_PROJECT_NAME** in Jenkins (or in a `.env` at repo root if Jenkins loads it) so the pipeline uses the correct network. The default project name in `docker-compose.yml` is `code-review`.

---

## Option 2: Run without Docker Compose

Use this to run the agent on your host against any supported SCM (e.g. GitHub, or a remote Gitea instance).

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS; on Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure environment

Copy `.env.example` to `.env` and set at least:

- **SCM**: `SCM_PROVIDER`, `SCM_URL`, `SCM_TOKEN` (and for Gitea: URL like `http://localhost:3000` or your Gitea host).
- **LLM**: `LLM_PROVIDER`, `LLM_MODEL`, and the provider key (e.g. `GOOGLE_API_KEY`, `OPENAI_API_KEY`).

Optional: `SCM_SKIP_LABEL`, `SCM_SKIP_TITLE_PATTERN`. See [Configuration](#configuration) and `.env.example`.

### 3. Run a review

```bash
code-review review --owner <owner> --repo <repo> --pr <pr_number> --head-sha <commit_sha>
```

Example for a GitHub PR:

```bash
export SCM_PROVIDER=github
export SCM_URL=https://api.github.com
export SCM_TOKEN=ghp_...
export LLM_PROVIDER=gemini
export GOOGLE_API_KEY=...
code-review review --owner myorg --repo myrepo --pr 42 --head-sha abc123...
```

You can also use a `.env` file (e.g. with `dotenv` or by sourcing it) instead of exporting variables.

### One-shot run with Docker (no Compose)

If you only want the agent in Docker but no Gitea/Jenkins:

```bash
docker build -t code-review-agent -f docker/Dockerfile.agent .
docker run --rm \
  -e SCM_PROVIDER=github \
  -e SCM_URL=https://api.github.com \
  -e SCM_TOKEN=ghp_... \
  -e SCM_OWNER=myorg \
  -e SCM_REPO=myrepo \
  -e SCM_PR_NUM=42 \
  -e SCM_HEAD_SHA=abc123... \
  -e LLM_PROVIDER=gemini \
  -e GOOGLE_API_KEY=... \
  code-review-agent review --owner myorg --repo myrepo --pr 42 --head-sha abc123...
```

---

## Configuration

| Variable | Description |
|----------|-------------|
| `SCM_PROVIDER` | `gitea`, `github`, `gitlab`, or `bitbucket` |
| `SCM_URL` | SCM API base URL (e.g. `http://gitea:3000`, `https://api.github.com`) |
| `SCM_TOKEN` | API token with repo read + comment scope |
| `LLM_PROVIDER` | `gemini`, `openai`, `anthropic`, `ollama`, etc. |
| `LLM_MODEL` | Model name (e.g. `gemini-2.5-flash`) |
| `SCM_SKIP_LABEL` | (Optional) PR label to skip review |
| `SCM_SKIP_TITLE_PATTERN` | (Optional) PR title substring to skip review |

See `.env.example` in the repo root for a full list and provider-specific keys (`GOOGLE_API_KEY`, `OPENAI_API_KEY`, etc.).

---

## Next steps

- **Security (CI)**: Use least-privilege tokens; restrict container egress. See README.
- **Observability**: Optional Prometheus/OpenTelemetry — see README and [Developer Guide](DEVELOPER_GUIDE.md).
- **Development**: Install dev deps and run tests — see README.
