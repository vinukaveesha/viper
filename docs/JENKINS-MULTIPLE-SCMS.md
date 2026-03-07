# Running the code-review agent with multiple SCMs

If your team uses **more than one SCM** (e.g. Gitea and GitHub, or GitHub and Bitbucket Data Center), run **one folder and one pipeline job per SCM**. Each job uses a **wrapper** script that sets `SCM_PROVIDER` and `SCM_URL` for that SCM, then runs the same pipeline. Global environment variables cannot define different values per job, so the wrapper is required for multi-SCM.

---

## Pipeline script source

The **Jenkinsfile** and **Jenkinsfile.multi-scm-wrapper** are each **self-contained** (no external load). You can use **Pipeline script from SCM** with the appropriate Script Path, or paste the entire file into **Pipeline script** (inline).

- **Single SCM**: Use **Script Path** `docker/jenkins/Jenkinsfile` (from SCM) or paste the contents of that file. See [Jenkins (existing installation)](JENKINS-EXISTING.md).
- **Multiple SCMs**: Each job needs a script that sets **that SCM’s** `SCM_PROVIDER` and `SCM_URL`. Use **one copy of the wrapper per SCM** (in the repo or pasted with the two env lines edited). Details below.

---

## 1. One wrapper file per SCM

The repo provides a single wrapper that sets SCM env vars and runs the full pipeline (self-contained):

- **`docker/jenkins/Jenkinsfile.multi-scm-wrapper`** – sets `env.SCM_PROVIDER` and `env.SCM_URL` at the top, then the same pipeline as single-SCM.

**For multiple SCMs you need one script path per SCM.** Two jobs cannot share the same wrapper file and have different `SCM_PROVIDER`/`SCM_URL` values. So:

1. **In your clone of this repo** (or your fork), create a **copy** of the wrapper for each SCM, for example:
   - `docker/jenkins/Jenkinsfile.wrapper-gitea`
   - `docker/jenkins/Jenkinsfile.wrapper-github`
2. In each copy, **edit only the two lines** at the top to match that SCM:

   ```groovy
   env.SCM_PROVIDER = 'gitea'   // or 'github', 'gitlab', 'bitbucket'
   env.SCM_URL = 'https://gitea.example.com'   // your SCM API URL
   ```

   Examples:
   - Gitea: `env.SCM_PROVIDER = 'gitea'`, `env.SCM_URL = 'https://gitea.example.com'`
   - GitHub: `env.SCM_PROVIDER = 'github'`, `env.SCM_URL = 'https://api.github.com'`
   - GitLab: `env.SCM_PROVIDER = 'gitlab'`, `env.SCM_URL = 'https://gitlab.com'` (or your GitLab URL)
   - Bitbucket DC: `env.SCM_PROVIDER = 'bitbucket'`, `env.SCM_URL = 'https://bitbucket.example.com/rest/api/1.0'`

3. **Commit and push** so Jenkins can check out these files when it runs “Pipeline script from SCM”.
4. When creating each Jenkins job, set **Script Path** to the **corresponding** wrapper file (e.g. the Gitea job uses `docker/jenkins/Jenkinsfile.wrapper-gitea`, the GitHub job uses `docker/jenkins/Jenkinsfile.wrapper-github`).

Do **not** point two jobs at the same wrapper file and try to “edit the file for each job”—the file has one content per path. Each SCM needs its own file in the repo and its own Script Path in Jenkins.

---

## 2. One folder and one job per SCM

| Step | What to do |
|------|------------|
| **Folder** | Create a folder per SCM (e.g. `code-review-gitea`, `code-review-github`). |
| **Credentials** | In the folder: **Credentials** → click **Global** domain → **Add credentials**. Add **Secret text** with ID `SCM_TOKEN` (token for that SCM) and `GOOGLE_API_KEY`. |
| **Pipeline job** | Inside the folder, create a **Pipeline** job (e.g. `code-review`). **Pipeline script from SCM** → this repo (your clone or fork that contains the wrapper copies), **Script Path**: the wrapper file for this SCM (e.g. `docker/jenkins/Jenkinsfile.wrapper-gitea`). Do **not** use `docker/jenkins/Jenkinsfile` here—that script expects global env and is for single-SCM only. |
| **Webhook** | In each SCM, point the repo webhook to **this job’s** Generic Webhook Trigger URL. Use the JSONPath for that SCM (Gitea/GitHub/GitLab: [JENKINS-EXISTING](JENKINS-EXISTING.md#4-webhooks-so-prs-trigger-the-job); Bitbucket DC: [Bitbucket Data Center](BITBUCKET-DATACENTER.md)). |

No global `SCM_PROVIDER` / `SCM_URL` are needed for these jobs; the wrapper sets them per job.

---

## 3. Example: Gitea + GitHub

1. **In the repo**: Create `docker/jenkins/Jenkinsfile.wrapper-gitea` (copy of `Jenkinsfile.multi-scm-wrapper` with `env.SCM_PROVIDER = 'gitea'`, `env.SCM_URL = 'https://gitea.example.com'`) and `docker/jenkins/Jenkinsfile.wrapper-github` (copy with `env.SCM_PROVIDER = 'github'`, `env.SCM_URL = 'https://api.github.com'`). Commit and push.

2. **Folder `code-review-gitea`**  
   - Credentials in folder: `SCM_TOKEN` = Gitea token, `GOOGLE_API_KEY`.  
   - Job `code-review`: **Pipeline script from SCM** → this repo, **Script Path** = `docker/jenkins/Jenkinsfile.wrapper-gitea`.  
   - Webhook: Gitea repos → this job’s webhook URL.

3. **Folder `code-review-github`**  
   - Credentials in folder: `SCM_TOKEN` = GitHub token, `GOOGLE_API_KEY`.  
   - Job `code-review`: **Pipeline script from SCM** → this repo, **Script Path** = `docker/jenkins/Jenkinsfile.wrapper-github`.  
   - Webhook: GitHub repos → this job’s webhook URL.

Each PR triggers only the pipeline for its SCM; credentials and SCM URL are isolated per folder/job.

---

## 4. Bitbucket Data Center

Same pattern: create a copy of the wrapper (e.g. `docker/jenkins/Jenkinsfile.wrapper-bitbucket`) with `env.SCM_PROVIDER = 'bitbucket'` and `env.SCM_URL = 'https://bitbucket.example.com/rest/api/1.0'`, commit and push. Create a folder and job for Bitbucket DC, set **Script Path** to that file. Use the Bitbucket webhook JSONPath and filter from [Bitbucket Data Center](BITBUCKET-DATACENTER.md).

---

## 5. Summary

- **Single SCM**: Use **Script Path** `docker/jenkins/Jenkinsfile` and set **global** env vars (`SCM_PROVIDER`, `SCM_URL`) in Jenkins. See [Jenkins (existing installation)](JENKINS-EXISTING.md).
- **Multiple SCMs**: Create **one copy of** `Jenkinsfile.multi-scm-wrapper` **per SCM** (e.g. in the repo as `Jenkinsfile.wrapper-gitea`, `Jenkinsfile.wrapper-github`, or paste into inline script with the two env lines edited). Point each job’s **Script Path** to that wrapper (or use inline script). Use folder-scoped credentials and one webhook URL per job. Pipelines are self-contained; SCM checkout is optional.
