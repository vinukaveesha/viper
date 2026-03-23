# SCM review decisions and merge blocking

Viper can submit a **PR-level review outcome** from the bot—**`APPROVE`** or **`REQUEST_CHANGES`**—based on how many **open** high- and medium-severity review signals still apply to the PR. For per-host definitions of “open”, see **Auto review decision** in [README.md](../README.md).

Each run **recomputes** those counts and may change the outcome. A **full** review after new commits does that automatically; for **discussion-only** changes (replies, deleted comments, resolved or outdated threads), you trigger **review-decision-only** jobs and optional **`CODE_REVIEW_EVENT_*`** mapping, as described in §1 and §2.

**Merge blocking** is decided by your SCM’s branch protection and merge checks, not by the API call alone. The rest of this document covers recalculation, setup, and the relevant **`SCM_REVIEW_DECISION_*`** / **`CODE_REVIEW_*`** variables ([Configuration reference](CONFIGURATION-REFERENCE.md)).

---

## 1. Concepts and recalculation

### 1.1 What a “review decision” is in Viper

When **`SCM_REVIEW_DECISION_ENABLED=true`**, the runner can submit a **PR-level** outcome after it knows how many **open** high- and medium-severity signals apply to the PR (see README for how “open” is defined per SCM).

| Submitted outcome | Meaning here |
|-------------------|--------------|
| **`APPROVE`** | From the bot’s perspective, open high/medium counts are **below** your thresholds — OK to merge in terms of this gate. |
| **`REQUEST_CHANGES`** | Counts meet or exceed thresholds — not OK until those signals are addressed, in the same sense as GitHub’s “request changes”. |

Thresholds: **`SCM_REVIEW_DECISION_HIGH_THRESHOLD`** and **`SCM_REVIEW_DECISION_MEDIUM_THRESHOLD`**. Implementation: `_quality_gate_high_medium_counts` and `_maybe_submit_review_decision` in `src/code_review/runner.py`.

### 1.2 Merge blocking comes from the SCM, not from the API alone

Submitting **`APPROVE`** or **`REQUEST_CHANGES`** over the API **does not by itself** turn merge on or off. Whether the merge button (or equivalent) is blocked depends on **your repository / branch settings**: protected branches, required reviews, approval rules, merge checks, and your **plan/tier** on hosts like GitLab or Bitbucket Cloud. People with **bypass** rights may still merge unless you disable that in policy.

Treat Viper’s decision as **input** into that native model: configure the host so the bot’s identity and its approve / needs-work state matter the way you intend.

### 1.3 Recalculation after code updates (new commits)

On a **normal** review run, the runner recomputes counts from **unresolved review items** the provider returns for the PR **plus** any **new** findings it is about to post (deduped). Then it may submit **`APPROVE`** / **`REQUEST_CHANGES`**.

When authors **push new commits**, CI typically reruns the full job; the idempotency key changes with the new **`head_sha`**, counts are fresh, and the submitted decision may change. How the SCM **replaces** an older bot review varies:

| Provider | Notes |
|----------|--------|
| **GitHub / Gitea** | A new review is posted; older ones can become outdated. GitHub’s gate counts skip outdated threads. |
| **GitLab** | Before **`REQUEST_CHANGES`**, an existing bot **approve** is cleared (`DELETE .../approve`, 404 ignored) so the bot is not both approved and requesting changes. |
| **Bitbucket Cloud** | Opposite state is cleared first (`DELETE` approve or request-changes); 404 ignored. |
| **Bitbucket Server / DC** | Participant status is updated in place (`PUT .../participants/{slug}`). |

This path does **not** use **reply-dismissal** (below); that exists only on **review-decision-only** runs with the right event context.

### 1.4 Recalculation when someone replies on a thread

Use **review-decision-only** (**`CODE_REVIEW_REVIEW_DECISION_ONLY=true`** or **`--review-decision-only`**) when a webhook or job runs after comment activity. It avoids the main review agent, so it is faster and uses fewer tokens. Map payload fields into **`CODE_REVIEW_EVENT_*`** ([Configuration reference](CONFIGURATION-REFERENCE.md) §5.1).

**Decision recalculation (every provider).** For **`CODE_REVIEW_EVENT_KIND=reply_added`**, a decision-only run behaves like any other decision-only run: the runner loads **open** high/medium signals from the **SCM API** for that PR and may submit **`APPROVE`** or **`REQUEST_CHANGES`**. That is true for **Bitbucket Cloud**, **Bitbucket Server / DC**, **Gitea**, **GitHub**, and **GitLab**. If the outcome does not change after a human reply, it is usually because the host still reports the same unresolved items (for example Bitbucket **tasks** or inline threads that stay open until resolved in the UI)—not because reply events are ignored.

**Optional reply-dismissal (GitHub and GitLab only).** **`CODE_REVIEW_REPLY_DISMISSAL_ENABLED`** adds a **separate** step: load the review thread, run a small LLM, and if the verdict is **`agreed`**, omit **that thread** from counts **for this run only** (not written back to the SCM). If **`disagreed`**, the runner may post a short follow-up on the thread when supported (unless **`--dry-run`**). This feature is **not** implemented on **Gitea**, **Bitbucket Cloud**, or **Bitbucket Server / DC**—leave it **`false`** there. With it **`true`** on those hosts, the runner records **`skipped_no_capability`** and still performs the normal recalculation above.

When reply-dismissal runs: replies from the **bot** are ignored (**`skipped_bot_author`**); LLM or parse errors apply **no** thread exclusion (**`llm_error`** / **`parse_failed`**).

**Optional early skip:** **`CODE_REVIEW_REVIEW_DECISION_ONLY_SKIP_IF_BOT_NOT_BLOCKING`** — for **`reply_added`** with event context, skip the run if the provider reports the token user is **not** in a blocking review state (providers without that query never skip on this path).

Prometheus: **`code_review_reply_dismissal_total{outcome=...}`** when metrics are enabled.

### 1.5 Recalculation when comments are deleted or threads change

For **`comment_deleted`**, **`thread_resolved`**, **`thread_outdated`**, **`scheduled`**, or empty / generic event context, review-decision-only recomputes from the **provider’s view of unresolved items** only. **No** reply-dismissal LLM runs. After a delete or resolve, the SCM usually drops that signal from “open” counts; the next job submits **`APPROVE`** / **`REQUEST_CHANGES`** from that state.

---

## 2. Setup

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
2. Set **`CODE_REVIEW_EVENT_KIND`**, **`CODE_REVIEW_EVENT_COMMENT_ID`**, and related **`CODE_REVIEW_EVENT_*`** from the payload ([Configuration reference](CONFIGURATION-REFERENCE.md) §5.1).
3. Enable **`SCM_REVIEW_DECISION_ENABLED`** on that job so the new counts produce a submission.
4. Optionally enable **`CODE_REVIEW_REPLY_DISMISSAL_ENABLED`** for **`reply_added`** on **GitHub or GitLab** only; on Bitbucket and Gitea, decision-only recalculation still runs without it (see §1.4).
5. Jenkins: see **`CODE_REVIEW_JENKINS_DECISION_ONLY_ACTIONS`** and [Bitbucket Data Center (Jenkins)](BITBUCKET-DATACENTER.md) for **`bitbucket_server`** webhook wiring.

### 2.6 Verify

Use **`--dry-run`** to inspect counts and logs without posting comments or submitting a review decision.

---

## Related reading

- [Configuration reference](CONFIGURATION-REFERENCE.md) — all `SCM_REVIEW_DECISION_*` and `CODE_REVIEW_*` variables
- [Developer guide](DEVELOPER_GUIDE.md) — `ProviderInterface`, `ReviewOrchestrator`, extension points
- `README.md` — quality gate semantics and per-SCM “open” behaviour
