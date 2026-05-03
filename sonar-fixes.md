# Sonar Fixes — PR #105

**Source:** https://sonarcloud.io/dashboard?id=e4c5_viper&pullRequest=105  
**Generated:** 2026-05-04

## Summary

| Severity | Count |
|----------|-------|
| MAJOR CODE_SMELL | 3 |
| Security Hotspots | 0 |
| Duplications | 0 (0.0% — all best value) |

No security hotspots. No code duplication. Three MAJOR code smells, all confirmed against current code.

---

## Findings (priority order)

### 1. Unused parameter `llm_cfg` in `_execute_review_agent`

- **File:** [src/code_review/orchestration/standard_review.py:403](src/code_review/orchestration/standard_review.py#L403)  
- **Rule:** `python:S1172` — Unused function parameters should be removed  
- **Effort:** 5 min  

**Current signature:**
```python
def _execute_review_agent(
    self,
    provider: ProviderInterface,
    cfg: Any,
    llm_cfg: Any,          # <-- unused; never referenced in body
    agent_llm_config: Any | None,
    ...
```

**Fix:** Remove `llm_cfg` from the method signature and remove it from the call site at line 700–709 (the caller passes `llm_cfg` as the third positional arg; remove that argument).

```python
# standard_review.py:399 — remove llm_cfg parameter
def _execute_review_agent(
    self,
    provider: ProviderInterface,
    cfg: Any,
    agent_llm_config: Any | None,
    app_cfg: Any,
    run_observability: ReviewRunObservability,
    env: _ReviewEnv,
    review_standards: Any,
) -> _ReviewExecution:

# standard_review.py:700 — remove llm_cfg from call
execution = self._execute_review_agent(
    provider,
    cfg,
    agent_llm_config,
    app_cfg,
    run_observability,
    env,
    review_standards,
)
```

---

### 2. `ReviewOrchestrator.__init__` has too many parameters (14 > 13)

- **File:** [src/code_review/orchestration/orchestrator.py:31](src/code_review/orchestration/orchestrator.py#L31)  
- **Rule:** `python:S107` — Functions/methods should not have too many parameters  
- **Effort:** 20 min  

**Parameters:** `owner`, `repo`, `pr_number`, `head_sha`, `dry_run`, `print_findings`, `review_decision_enabled`, `review_decision_high_threshold`, `review_decision_medium_threshold`, `review_decision_only`, `event_context`, `scm_config`, `llm_config`, `app_config`

**Fix options (choose one):**

*Option A — Extract `ReviewDecisionConfig` dataclass* (minimal change, keeps call sites almost identical):
```python
@dataclass
class ReviewDecisionConfig:
    enabled: bool | None = None
    high_threshold: int | None = None
    medium_threshold: int | None = None
    only: bool = False
    event_context: ReviewDecisionEventContext | None = None

# __init__ drops to 9 parameters:
def __init__(
    self,
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str = "",
    *,
    dry_run: bool = False,
    print_findings: bool = False,
    review_decision: ReviewDecisionConfig | None = None,
    scm_config: SCMConfig | None = None,
    llm_config: LLMConfig | None = None,
    app_config: CodeReviewAppConfig | None = None,
):
```

*Option B — Accept `**kwargs` for review-decision overrides* (shorter but less type-safe).

**Note:** `run_review()` in `runner.py` has the identical parameter list (see finding #3 below). Applying the same dataclass to both keeps them in sync.

---

### 3. `run_review` function has too many parameters (14 > 13)

- **File:** [src/code_review/runner.py:51](src/code_review/runner.py#L51)  
- **Rule:** `python:S107` — Functions/methods should not have too many parameters  
- **Effort:** 20 min  

**Parameters:** identical to `ReviewOrchestrator.__init__` above.

**Fix:** Apply the same `ReviewDecisionConfig` dataclass from finding #2 to this function signature:
```python
def run_review(
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str = "",
    *,
    dry_run: bool = False,
    print_findings: bool = False,
    review_decision: ReviewDecisionConfig | None = None,
    scm_config: SCMConfig | None = None,
    llm_config: LLMConfig | None = None,
    app_config: CodeReviewAppConfig | None = None,
) -> list[FindingV1]:
```

Update `__main__.py` and any other callers that pass `review_decision_*` kwargs individually to construct a `ReviewDecisionConfig` instead.

---

## Verification Notes

- All three findings verified against the current branch (`celery`) — code matches the Sonar-reported lines exactly.
- No duplications to fix (0.0% across all 18 files in the PR).
- Finding #1 (unused param) is the lowest-risk, fastest win — 5 min, one-line removal.
- Findings #2 and #3 are coupled: the same dataclass should be introduced once and shared, so address them together.
