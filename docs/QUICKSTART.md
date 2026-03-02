# Quick Start Guide (Docker Only)

Get the code review agent running quickly with **Docker Compose** (Gitea + Jenkins) and **auto-triggered PR reviews**.

---

## Prerequisites

- **Docker** and **Docker Compose**
- **LLM API key** (e.g. `GOOGLE_API_KEY` for Gemini, or `OPENAI_API_KEY` for OpenAI)

---

## 1. Start the stack

From the **repository root** (the folder that contains `docker-compose.yml`):

```bash
docker compose up -d --build
```

If you use Podman Compose instead:

```bash
podman-compose up -d --build
```

- **Gitea**: http://localhost:3000  
- **Jenkins**: http://localhost:8080  

**Note (Docker vs Podman):**
- Docker users: no changes needed.
- Podman users: set `CONTAINER_SOCKET` to your rootless Podman socket before starting:
  - Example: `export CONTAINER_SOCKET=$XDG_RUNTIME_DIR/podman/podman.sock`
  - Then run `podman-compose up -d --build`
- Podman users only: uncomment `CONTAINER_RUNTIME: podman` in `docker-compose.yml` so Jenkins uses Podman instead of Docker.

---

## 2. Configure Gitea

1. Open http://localhost:3000 and complete first-run setup (admin user, etc.).
2. Create a **repository** (e.g. `myrepo`) under a user or org (e.g. `myorg`).
3. Create an **API token**: **Settings → Applications → Generate New Token** (scope: read/write for the repo).
4. If webhooks fail with **“webhook can only call allowed HTTP servers”**, ensure `docker-compose.yml` includes:
   - `GITEA__webhook__ALLOWED_HOST_LIST: jenkins,jenkins:8080`

---

## 3. Configure Jenkins

1. Open http://localhost:8080. Default credentials are `admin` / `admin` (from `docker-compose.yml`).
2. The **Jenkins job is auto-created** via JCasC as `code-review` (no manual job setup required). It loads its pipeline from `docker/jenkins/Jenkinsfile` (mounted into the Jenkins container).
3. **Credentials** (required):
   - Option A: set `SCM_TOKEN` and `GOOGLE_API_KEY` in `docker-compose.yml` before first boot.
   - Option B: add them in **Manage Jenkins → Credentials → Global** as **Secret text** IDs.
4. Manual runs: use **Build with Parameters** on the `code-review` job.
5. Webhook runs: `SCM_*` are injected automatically as environment variables by the webhook trigger.

**How environment variables are set (clarity):**
- `docker compose` reads a `.env` file **only** to substitute values in `docker-compose.yml`. It does **not** inject those values into Jenkins jobs.
- Jenkins job env vars come from **Credentials**, **build parameters**, or **webhook variables** (below).
- In this setup, the Jenkinsfile sets `SCM_TOKEN`/`GOOGLE_API_KEY` from **Credentials**, and sets `SCM_OWNER`/`SCM_REPO`/`SCM_PR_NUM`/`SCM_HEAD_SHA` from **webhook variables** (or from build parameters if you trigger manually).

---

## 4. Build the agent image

From the repository root:

```bash
docker build -t code-review-agent -f docker/Dockerfile.agent .
```

---

## 5. Auto-trigger PR reviews (Gitea webhook → Jenkins)

The Jenkins job is preconfigured (via JCasC) with a **Generic Webhook Trigger** and JSONPath mappings:

- `SCM_OWNER` → `$.pull_request.base.repo.owner.login`
- `SCM_REPO` → `$.pull_request.base.repo.name`
- `SCM_PR_NUM` → `$.pull_request.number`
- `SCM_HEAD_SHA` → `$.pull_request.head.sha`

### 5.1 Configure the Gitea webhook

1. In Gitea, open your repo → **Settings → Webhooks → Add Webhook → Gitea**.
2. **Target URL**: `http://jenkins:8080/generic-webhook-trigger/invoke`
3. **Content Type**: `application/json`.
4. **Trigger On**: **Pull Request**.
5. Save the webhook.

Now, when a PR is opened or updated, Jenkins will trigger the pipeline and run the review.

---

## Next steps

For a fuller development workflow (Docker + non-Docker paths), see **[Development Testing Guide](DEV_TESTING.md)**.
