"""Public runner entrypoint for code review orchestration."""

from __future__ import annotations

# -- Symbols from canonical domain modules (also available via orchestration_deps) --
from code_review.comments.manager import _build_ignore_set  # noqa: F401

# -- Core types --
from code_review.orchestration.filter import ReviewFilter  # noqa: F401
from code_review.orchestration.orchestrator import ReviewOrchestrator  # noqa: F401

# -- Symbols re-exported from orchestration_deps (defined there) --
from code_review.orchestration_deps import (  # noqa: F401
    AGENT_VERSION,
    _build_idempotency_key,
    _compute_quality_gate_review_outcome,
    _diff_visible_new_lines,
    _findings_from_response,
    _format_reply_dismissal_user_message,
    _generate_auto_pr_description,
    _idempotency_key_seen_in_comments,
    _maybe_post_started_review_comment,
    _normalize_path_for_anchor,
    _omit_marker_pr_summary_visible_text,
    _parse_findings_json,
    _post_comments_one_by_one,
    _reply_added_event_authored_by_bot,
)
from code_review.quality.outcome import QualityGateReviewOutcome  # noqa: F401
from code_review.refinement.filters.anchor_relocator import (  # noqa: F401
    relocate_findings_by_anchor as _relocate_findings_by_anchor,
)
from code_review.refinement.filters.contradiction import (  # noqa: F401
    _message_describes_syntax_or_missing_token_issue,
)
from code_review.refinement.filters.patch_validator import (  # noqa: F401
    validate_suggested_patches as _validate_suggested_patches,
)
from code_review.refinement.filters.self_retraction import (  # noqa: F401
    _finding_message_looks_self_retracted,
)
from code_review.config import CodeReviewAppConfig, LLMConfig, SCMConfig
from code_review.schemas.findings import FindingV1
from code_review.schemas.review_decision_event import (
    ReviewDecisionConfig,  # noqa: F401
    ReviewDecisionEventContext,  # noqa: F401
    review_decision_event_context_from_env,
)


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
    """
    Run the code review agent (findings-only mode). Fetches existing comments,
    runs agent, parses findings, filters by ignore list, and posts via provider.
    Returns list of findings that were posted (or would be posted if dry_run).

    *review_decision* groups per-run overrides (enabled flag, thresholds, only-mode,
    and event context). These apply only to this run and do not mutate the
    process-global cached :func:`~code_review.config.get_scm_config` instance.

    When ``review_decision.only`` is True (or ``CODE_REVIEW_REVIEW_DECISION_ONLY`` is set),
    skips the agent, inline posting, and idempotency short-circuit; only recomputes the
    quality gate and submits a PR review decision when enabled in SCM config.

    *scm_config*, *llm_config*, and *app_config* may be supplied programmatically to bypass
    process environment loading. When omitted, the existing environment-driven
    configuration path is preserved.
    """
    import dataclasses

    rd = review_decision or ReviewDecisionConfig()
    resolved_event = rd.event_context or review_decision_event_context_from_env()
    orchestrator = ReviewOrchestrator(
        owner,
        repo,
        pr_number,
        head_sha,
        dry_run=dry_run,
        print_findings=print_findings,
        review_decision=dataclasses.replace(rd, event_context=resolved_event),
        scm_config=scm_config,
        llm_config=llm_config,
        app_config=app_config,
    )
    return orchestrator.run()
