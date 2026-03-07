# Running the code-review agent with multiple SCMs

If your team uses **more than one SCM** (e.g. Gitea and GitHub, or GitHub and Bitbucket Data Center), run **one folder and one pipeline job per SCM**. Each job uses a **wrapper** script that sets `SCM_PROVIDER` and `SCM_URL` for that SCM, then runs the same main pipeline. Global environment variables cannot define different values per job, so the wrapper is required for multi-SCM.

---

## 1. Wrapper pipeline (per-SCM script)

The repo provides a single wrapper that sets SCM env vars and then runs the main pipeline:

- **`docker/jenkins/Jenkinsfile.multi-scm-wrapper`** – set `SCM_PROVIDER` and `SCM_URL` at the top, then `load 'docker/jenkins/mainPipeline.groovy'`.

**For each SCM:**

1. Point the job’s **Script Path** to `docker/jenkins/Jenkinsfile.multi-scm-wrapper` (or to a copy you make for that SCM).
2. Edit the **two lines** at the top of the file (or your copy) for this SCM:

   ```groovy
   env.SCM_PROVIDER = 'gitea'   // or 'github', 'gitlab', 'bitbucket'
   env.SCM_URL = 'https://gitea.example.com'   // your SCM API URL
   ```

   Examples:
   - Gitea: `env.SCM_PROVIDER = 'gitea'`, `env.SCM_URL = 'https://gitea.example.com'`
   - GitHub: `env.SCM_PROVIDER = 'github'`, `env.SCM_URL = 'https://api.github.com'`
   - GitLab: `env.SCM_PROVIDER = 'gitlab'`, `env.SCM_URL = 'https://gitlab.com'` (or your GitLab URL)
   - Bitbucket DC: `env.SCM_PROVIDER = 'bitbucket'`, `env.SCM_URL = 'https://bitbucket.example.com/rest/api/1.0'`

If you have **multiple SCMs**, use one job per SCM and either (a) point each job at the same wrapper and edit the file in the repo to match the job you’re configuring (one SCM at a time), or (b) copy the wrapper to a new file per SCM (e.g. in your branch), edit the two lines in each copy, and set **Script Path** to that copy so each job has its own SCM settings.

---

## 2. One folder and one job per SCM

| Step | What to do |
|------|------------|
| **Folder** | Create a folder per SCM (e.g. `code-review-gitea`, `code-review-github`). |
| **Credentials** | In the folder: **Credentials** → **Global** domain → **Add credentials**. Add **Secret text** with ID `SCM_TOKEN` (token for that SCM) and `GOOGLE_API_KEY`. |
| **Pipeline job** | Inside the folder, create a **Pipeline** job (e.g. `code-review`). **Pipeline script from SCM** → this repo, **Script Path**: `docker/jenkins/Jenkinsfile.multi-scm-wrapper` (or a copy you made for this SCM with the two env lines edited). Do **not** use `docker/jenkins/Jenkinsfile` here—that script expects global env and is for single-SCM only. |
| **Webhook** | In each SCM, point the repo webhook to **this job’s** Generic Webhook Trigger URL. Use the JSONPath for that SCM (Gitea/GitHub/GitLab: [JENKINS-EXISTING](JENKINS-EXISTING.md#4-webhooks-so-prs-trigger-the-job); Bitbucket DC: [Bitbucket Data Center](BITBUCKET-DATACENTER.md)). |

No global `SCM_PROVIDER` / `SCM_URL` are needed for these jobs; the wrapper sets them per job.

---

## 3. Example: Gitea + GitHub

1. **Folder `code-review-gitea`**  
   - Credentials in folder: `SCM_TOKEN` = Gitea token, `GOOGLE_API_KEY`.  
   - Job `code-review`: **Script Path** = `docker/jenkins/Jenkinsfile.multi-scm-wrapper` (with `SCM_PROVIDER = 'gitea'`, `SCM_URL = 'https://gitea.example.com'` in that file, or in a copy used only for this job).  
   - Webhook: Gitea repos → this job’s webhook URL.

2. **Folder `code-review-github`**  
   - Credentials in folder: `SCM_TOKEN` = GitHub token, `GOOGLE_API_KEY`.  
   - Job `code-review`: **Script Path** = `docker/jenkins/Jenkinsfile.multi-scm-wrapper` (with `SCM_PROVIDER = 'github'`, `SCM_URL = 'https://api.github.com'` in that file, or in a copy used only for this job).  
   - Webhook: GitHub repos → this job’s webhook URL.

Each PR triggers only the pipeline for its SCM; credentials and SCM URL are isolated per folder/job.

---

## 4. Bitbucket Data Center

Same pattern: one folder, one job, **Script Path** `docker/jenkins/Jenkinsfile.multi-scm-wrapper` (edit the two lines to `env.SCM_PROVIDER = 'bitbucket'` and `env.SCM_URL = 'https://bitbucket.example.com/rest/api/1.0'`, or use a copy). Use the Bitbucket webhook JSONPath and filter from [Bitbucket Data Center](BITBUCKET-DATACENTER.md).

---

## 5. Summary

- **Single SCM**: use **Script Path** `docker/jenkins/Jenkinsfile` and set **global** env vars (`SCM_PROVIDER`, `SCM_URL`) in Jenkins. See [Jenkins (existing installation)](JENKINS-EXISTING.md).
- **Multiple SCMs**: do **not** rely on global env for SCM; use **Script Path** `docker/jenkins/Jenkinsfile.multi-scm-wrapper` (edit the two env lines for this SCM, or use a copy per SCM). Use folder-scoped credentials and one webhook URL per job.
