# Running the code-review agent with multiple SCMs

If your team uses **more than one SCM** (e.g. Gitea and GitHub, or GitHub and Bitbucket Data Center), run **one folder and one pipeline job per SCM**. Each job uses the **same** Jenkinsfile (`docker/jenkins/Jenkinsfile`); you set **per-job parameter defaults** for `SCM_PROVIDER` and `SCM_URL` so each job talks to the right SCM. No wrapper file or repo copies needed.

---

## How it works

The Jenkinsfile defines optional parameters **`SCM_PROVIDER`** and **`SCM_URL`**. If those parameters have default values set for a job, the pipeline uses them for that job; otherwise it uses Jenkins global (or folder) environment variables. So:

- **Single SCM**: One job, **Script Path** `docker/jenkins/Jenkinsfile`. Set `SCM_PROVIDER` and `SCM_URL` in **Manage Jenkins → Global properties → Environment variables**. See [Jenkins (existing installation)](JENKINS-EXISTING.md).
- **Multiple SCMs**: One job **per** SCM, each with **Script Path** `docker/jenkins/Jenkinsfile`. In each job, set the **parameter defaults** for `SCM_PROVIDER` and `SCM_URL` (e.g. for the Gitea job: `gitea` and `https://gitea.example.com`). Use folder-scoped credentials and one webhook URL per job.

---

## 1. One folder and one job per SCM

| Step | What to do |
|------|------------|
| **Folder** | Create a folder per SCM (e.g. `code-review-gitea`, `code-review-github`). |
| **Credentials** | In the folder: **Credentials** → click **Global** domain → **Add credentials**. Add **Secret text** with ID `SCM_TOKEN` (token for that SCM) and `GOOGLE_API_KEY`. |
| **Pipeline job** | Inside the folder, create a **Pipeline** job (e.g. `code-review`). **Pipeline script from SCM** → this repo, **Script Path**: `docker/jenkins/Jenkinsfile`. In the job: **Configure → This project is parameterized** (or **Parameters**): find **SCM_PROVIDER** and **SCM_URL** and set their **default values** for this SCM (e.g. `gitea` and `https://gitea.example.com`). |
| **Webhook** | In each SCM, point the repo webhook to **this job’s** Generic Webhook Trigger URL. Use the JSONPath for that SCM (Gitea/GitHub/GitLab: [JENKINS-EXISTING](JENKINS-EXISTING.md#4-webhooks-so-prs-trigger-the-job); Bitbucket DC: [Bitbucket Data Center](BITBUCKET-DATACENTER.md)). |

No global `SCM_PROVIDER` / `SCM_URL` are needed for these jobs; the parameter defaults supply them per job.

---

## 2. Example: Gitea + GitHub

1. **Folder `code-review-gitea`**  
   - Credentials in folder: `SCM_TOKEN` = Gitea token, `GOOGLE_API_KEY`.  
   - Job `code-review`: **Pipeline script from SCM** → this repo, **Script Path** = `docker/jenkins/Jenkinsfile`. In job **Configure → Parameters**, set **default** for `SCM_PROVIDER` = `gitea`, **default** for `SCM_URL` = `https://gitea.example.com`.  
   - Webhook: Gitea repos → this job’s webhook URL.

2. **Folder `code-review-github`**  
   - Credentials in folder: `SCM_TOKEN` = GitHub token, `GOOGLE_API_KEY`.  
   - Job `code-review`: **Pipeline script from SCM** → this repo, **Script Path** = `docker/jenkins/Jenkinsfile`. In job **Configure → Parameters**, set **default** for `SCM_PROVIDER` = `github`, **default** for `SCM_URL` = `https://api.github.com`.  
   - Webhook: GitHub repos → this job’s webhook URL.

Each PR triggers only the pipeline for its SCM; credentials and SCM URL are isolated per folder/job.

---

## 3. Bitbucket Data Center

Same pattern: one folder, one job, **Script Path** `docker/jenkins/Jenkinsfile`. Set parameter defaults `SCM_PROVIDER` = `bitbucket`, `SCM_URL` = `https://bitbucket.example.com/rest/api/1.0`. Use the Bitbucket webhook JSONPath and filter from [Bitbucket Data Center](BITBUCKET-DATACENTER.md).

---

## 4. Summary

- **Single SCM**: One job, **Script Path** `docker/jenkins/Jenkinsfile`, **global** env vars `SCM_PROVIDER` and `SCM_URL`. See [Jenkins (existing installation)](JENKINS-EXISTING.md).
- **Multiple SCMs**: One job per SCM, same **Script Path** `docker/jenkins/Jenkinsfile`. Set each job’s **parameter defaults** for `SCM_PROVIDER` and `SCM_URL` in job **Configure → Parameters**. Use folder-scoped credentials and one webhook URL per job.
