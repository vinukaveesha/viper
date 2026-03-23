# SCM review decisions and merge blocking

Viper can submit a **PR-level review outcome** from the bot—**`APPROVE`** or **`REQUEST_CHANGES`**—based on how many **open** high- and medium-severity review signals still apply to the PR. For per-host definitions of “open”, see **Auto review decision** in [README.md](../README.md).

Each run **recomputes** those counts and may change the outcome. A **full** review after new commits does that automatically; for **discussion-only** changes (replies, deleted comments, resolved or outdated threads), the same gate logic runs in a lighter **review-decision-only** mode, typically triggered from CI or webhooks once you have configured it (**§2**).

**Merge blocking** is decided by your SCM’s branch protection and merge checks, not by the API call alone.

---

## 1. Concepts and recalculation

This section describes **runtime behaviour** only: what the runner does and when counts refresh. **§2** is where Viper settings, SCM host settings, env vars, and CLI flags are documented; the full variable list is in the [Configuration reference](CONFIGURATION-REFERENCE.md).

### 1.1 What a “review decision” is in Viper

When automatic review decisions are **enabled** (a Viper setting—**§2**), the runner can submit a **PR-level** outcome after it knows how many **open** high- and medium-severity signals apply to the PR (see [README.md](../README.md) for how “open” is defined per SCM).

| Submitted outcome | Meaning here |
|-------------------|--------------|
| **`APPROVE`** | From the bot’s perspective, open high/medium counts are **below** the configured cutoffs — OK to merge in terms of this gate. |
| **`REQUEST_CHANGES`** | Counts meet or exceed those cutoffs — not OK until those signals are addressed, in the same sense as GitHub’s “request changes”. |

How aggressive those cutoffs are is **configurable** in **§2**; this section does not define default or recommended values.

### 1.2 Merge blocking comes from the SCM, not from the API alone

Submitting **`APPROVE`** or **`REQUEST_CHANGES`** over the API **does not by itself** turn merge on or off. Whether the merge button (or equivalent) is blocked depends on **your repository / branch settings**: protected branches, required reviews, approval rules, merge checks, and your **plan/tier** on hosts like GitLab or Bitbucket Cloud. People with **bypass** rights may still merge unless you disable that in policy.

Treat Viper’s decision as **input** into that native model: the bot’s identity and its approve / needs-work state must be recognized under the host’s rules if you want merges to follow this gate. Aligning SCM branch rules with that intent is part of **§2**.

### 1.3 Recalculation after code updates (new commits)

On a **normal** review run, the runner recomputes counts from **unresolved review items** the provider returns for the PR **plus** any **new** findings it is about to post (deduped). Then it may submit **`APPROVE`** / **`REQUEST_CHANGES`**.

When authors **push new commits**, CI typically reruns the full job; the idempotency key changes with the new **`head_sha`**, counts are fresh, and the submitted decision may change. How the SCM **replaces** an older bot review varies:

| Provider | Notes |
|----------|--------|
| **GitHub / Gitea** | A new review is posted; older ones can become outdated. GitHub’s gate counts skip outdated threads. |
| **GitLab** | Before **`REQUEST_CHANGES`**, an existing bot **approve** is cleared (`DELETE .../approve`, 404 ignored) so the bot is not both approved and requesting changes. |
| **Bitbucket Cloud** | Opposite state is cleared first (`DELETE` approve or request-changes); 404 ignored. |
| **Bitbucket Server / DC** | Participant status is updated in place (`PUT .../participants/{slug}`). |

The push path does **not** run **reply-dismissal**; that optional behaviour exists only on **review-decision-only** runs when someone replies (**§1.4**).

### 1.4 Recalculation when someone replies on a thread

After comment activity, you can run the tool in **review-decision-only** mode so it skips the main review agent: less work and fewer tokens than a full review. **§2** describes how to hook that up from webhooks or CI.

When the triggering event is a **reply on a thread**, decision-only still reloads **open** high/medium signals from the SCM and may submit **`APPROVE`** or **`REQUEST_CHANGES`**. If the outcome does not change after a human reply, the host usually still reports the same unresolved items—for example **Bitbucket Cloud** still counts **open inline comments and open tasks** until they are resolved in the UI; **Bitbucket Server / DC** is the same for comments plus tasks. Replies are not ignored; the SCM state simply has not changed yet.

**Optional reply-dismissal.** If turned on in configuration (**§2**), an extra step can load the **PR review-comment** thread, run a small LLM, and—if it judges the reply sufficient—**omit that thread from counts for this run only** (nothing is written back to the SCM as “resolved”). If it judges the reply insufficient, the runner may post a brief follow-up **on that comment thread** where the API allows.

Implemented for **GitHub**, **GitLab**, **Bitbucket Cloud**, and **Bitbucket Server / DC**. For **Bitbucket**, threading and exclusion apply to **inline pull request comments** (parent / reply links in the REST model). The quality gate uses **`comment:{root_comment_id}`** for those items so the excluded id matches what the gate counts. **Gitea** does not implement this path yet (`skipped_no_capability`); recalculation still uses full SCM-derived counts.

**Requirement:** the webhook / event must supply the **comment** id of the new reply (or any comment in the thread, depending on your mapping)—not e.g. a **Bitbucket PR task** id. If the id does not resolve to a comment thread with at least two messages, the dismissal step is skipped (`skipped_insufficient_thread`) while decision-only recalculation still runs.

### 1.5 Recalculation when comments are deleted or threads change

For **deleted comments**, **resolved** or **outdated** threads, **scheduled** jobs, or **no specific event**, a decision-only run recomputes from the **provider’s view of unresolved items** only. No reply-dismissal LLM runs. After a delete or resolve, the SCM usually drops that signal from “open” counts; the next run may then submit **`APPROVE`** instead of **`REQUEST_CHANGES`**. How webhook payloads map to these runs is **§2**.

---

## 2. Setup

Environment variables and CLI equivalents for everything below are summarized in the [Configuration reference](CONFIGURATION-REFERENCE.md).

### 2.1 Enable review decisions in Viper

| Setting | Purpose |
|---------|---------|
| **`SCM_REVIEW_DECISION_ENABLED=true`** | Turn on submission of **`APPROVE`** / **`REQUEST_CHANGES`**. |
| **`SCM_REVIEW_DECISION_HIGH_THRESHOLD`** / **`SCM_REVIEW_DECISION_MEDIUM_THRESHOLD`** | When to submit **`REQUEST_CHANGES`** vs **`APPROVE`**. Start conservative in production. |
| **`SCM_BITBUCKET_SERVER_USER_SLUG`** | **Bitbucket Server / DC only:** username slug of the token user. Required for review decisions on that provider; if unset, submission is skipped. |

CLI overrides exist for some of these; see [Configuration reference](CONFIGURATION-REFERENCE.md).

### 2.2 Which providers submit decisions

| `SCM_PROVIDER` | Submits bot approve / request-changes? |
|----------------|----------------------------------------|
| **`github`** | Yes |
| **`gitea`** | Yes (server must support the review API) |
| **`gitlab`** | Yes (approve API + MR note / review flow for request-changes) |
| **`bitbucket`** (Cloud) | Yes |
| **`bitbucket_server`** | Yes when **`SCM_BITBUCKET_SERVER_USER_SLUG`** is set |

If submission is disabled or unsupported, inline comments can still work while decisions do not.

### 2.3 Configure merge blocking on each host

Use native docs for the exact UI. Below: what to turn on so Viper’s outcomes can **block merge** when you want that.

| SCM | What to configure (summary) | Official docs |
|-----|-----------------------------|---------------|
| **GitHub** | Branch protection: require PR reviews; **Request changes** blocks merge until cleared or dismissed. Optional: disallow bypass. | [PR reviews](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews), [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) |
| **Gitea** | Protected branch: **Block merge on rejected reviews**; optional: admins must follow rules. | [Protected branches](https://docs.gitea.com/usage/access-control/protected-branches) |
| **GitLab** | Approvals / **Request changes** blocking depends on **tier** and project settings (e.g. prevent merge when changes requested). | [MR approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/), [MR reviews](https://docs.gitlab.com/ee/user/project/merge_requests/reviews/) |
| **Bitbucket Cloud** | Branch restrictions and merge checks (approvals, no changes requested, tasks, builds). Strict **prevent merge** may require **Premium**. | [Checks before merge](https://support.atlassian.com/bitbucket-cloud/docs/suggest-or-require-checks-before-a-merge/) |
| **Bitbucket Server / DC** | Branch merge checks (approvals, needs-work, tasks, builds). | [Checks for merging PRs](https://confluence.atlassian.com/spaces/BitbucketServer/pages/776640039/Checks+for+merging+pull-requests) |

Ensure the **bot account** is treated as a valid reviewer where your rules count approvals or “changes requested”.

### 2.4 Token permissions

The token must be allowed to **submit** the same outcomes you rely on (REST scopes / permissions for reviews, approvals, MR notes on GitLab, participant **`PUT`** on Bitbucket Server for the configured slug). Narrow scopes often break **decisions** while **posting comments** still works.

### 2.5 Optional: comment-driven recomputation

1. Run **`code-review --review-decision-only`** (or set **`CODE_REVIEW_REVIEW_DECISION_ONLY`**) from CI when webhooks fire on comment activity.
2. Set **`CODE_REVIEW_EVENT_KIND`**, **`CODE_REVIEW_EVENT_COMMENT_ID`**, and related **`CODE_REVIEW_EVENT_*`** from the payload ([Configuration reference](CONFIGURATION-REFERENCE.md) §5.1). Use **`reply_added`** when a human replied on a thread; use **`comment_deleted`**, **`thread_resolved`**, **`thread_outdated`**, or **`scheduled`** when you only need a fresh count from SCM state (no reply-dismissal LLM). For **`reply_added`** with reply-dismissal, **`CODE_REVIEW_EVENT_COMMENT_ID`** must be the SCM’s **pull request review comment** id (the reply or another comment in the same thread)—**not** a Bitbucket **task** id or other object type, or thread loading will fail and you will see **`skipped_insufficient_thread`** in metrics/logs.
3. Enable **`SCM_REVIEW_DECISION_ENABLED`** on that job so the new counts produce a submission.
4. **Reply-dismissal:** set **`CODE_REVIEW_REPLY_DISMISSAL_ENABLED=true`** if you want the optional LLM step on **`reply_added`** (supported on GitHub, GitLab, Bitbucket Cloud, Bitbucket Server / DC; not on **Gitea**—there **`skipped_no_capability`** if enabled). Bot-authored replies are ignored (**`skipped_bot_author`**); LLM or parse failure applies no exclusion (**`llm_error`** / **`parse_failed`**). Thread follow-ups respect **`--dry-run`**. Observability: **`code_review_reply_dismissal_total{outcome=...}`** when Prometheus is enabled ([Configuration reference](CONFIGURATION-REFERENCE.md) §7).
5. **Skip idle jobs:** **`CODE_REVIEW_REVIEW_DECISION_ONLY_SKIP_IF_BOT_NOT_BLOCKING`** — for **`reply_added`** with event context, skip the run when the provider reports the token user is **not** in a blocking review state (providers without that capability never skip here).
6. Jenkins: **`CODE_REVIEW_JENKINS_DECISION_ONLY_ACTIONS`** and [Bitbucket Data Center (Jenkins)](BITBUCKET-DATACENTER.md) for **`bitbucket_server`** webhook wiring.

### 2.6 Verify

Use **`--dry-run`** to inspect counts and logs without posting comments or submitting a review decision.

---

## Related reading

- [Configuration reference](CONFIGURATION-REFERENCE.md) — all `SCM_REVIEW_DECISION_*` and `CODE_REVIEW_*` variables
- [Developer guide](DEVELOPER_GUIDE.md) — `ProviderInterface`, `ReviewOrchestrator`, extension points
- `README.md` — quality gate semantics and per-SCM “open” behaviour
