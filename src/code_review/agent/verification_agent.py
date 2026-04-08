"""Verification agent: second-opinion LLM pass for medium/low-confidence findings.

The main review agent stays conservative and labels uncertain findings with
confidence="medium" or confidence="low".  Rather than silently dropping them in
the refinement pipeline, this module runs a targeted verification call that
presents each flagged finding alongside the relevant code snippet and asks the
LLM to confirm or reject the concern.

Only findings with confidence "medium" or "low" are sent for verification.
High-confidence findings (and findings where confidence is None / unset) bypass
verification entirely.
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, Field

from code_review.schemas.findings import FindingV1

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

_MAX_FINDINGS_PER_BATCH = 20  # avoid token blow-up on large PRs


class _VerificationVerdict(BaseModel):
    """Verdict for one finding in the verification batch."""

    index: int = Field(..., description="Zero-based index matching the input finding list")
    verdict: Literal["confirm", "reject"] = Field(
        ..., description="confirm if the concern is valid; reject if the code is fine"
    )
    reason: str = Field(..., description="One-sentence explanation of the decision")


class _VerificationResult(BaseModel):
    """Structured output for the verification agent."""

    model_config = {"extra": "ignore"}

    verdicts: list[_VerificationVerdict] = Field(
        default_factory=list,
        description="One verdict per input finding, matched by index",
    )


# ---------------------------------------------------------------------------
# Instruction
# ---------------------------------------------------------------------------

_VERIFICATION_INSTRUCTION = """\
You are an expert code reviewer performing a second-opinion check on flagged findings.

For each finding you receive you will see:
- index: integer (used to match your verdict back to the finding)
- file: the source file path
- line: the line number in the new-file view
- message: the reviewer's concern
- evidence: brief code quote supporting the concern (may be empty)
- code_snippet: the relevant lines from the diff, with n: line-number annotations

Your task: decide whether each finding is a REAL problem visible in the code snippet.

Output a JSON object {"verdicts": [...]} with one verdict per finding:
  - index: same integer as the input
  - verdict: "confirm" if the concern is real, "reject" if the code shown is fine
  - reason: one concise sentence

Rules:
- "confirm" when the issue is directly visible in the code_snippet.
- "reject" when the code_snippet contradicts the concern, or the problem is not
  observable from the information provided.
- If genuinely uncertain, prefer "confirm" — a false positive that reaches the
  pipeline is safer than a real bug that is silently dropped.
- Do NOT invent concerns beyond what the message describes.
- Keep reason to one sentence.
"""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def create_verification_agent():
    """Create the lightweight verification ADK agent."""
    from google.adk.agents import Agent
    from google.genai import types

    from code_review.config import get_llm_config
    from code_review.models import get_configured_model

    llm_cfg = get_llm_config()
    generate_content_config = types.GenerateContentConfig(
        temperature=0.1,  # deterministic: this is a binary confirm/reject task
        max_output_tokens=min(llm_cfg.max_output_tokens, 4096),
    )
    return Agent(
        model=get_configured_model(),
        name="verification_agent",
        instruction=_VERIFICATION_INSTRUCTION,
        output_schema=_VerificationResult,
        generate_content_config=generate_content_config,
    )


# ---------------------------------------------------------------------------
# Code snippet extraction helper
# ---------------------------------------------------------------------------


def _extract_snippet_for_finding(finding: FindingV1, diff_text: str, radius: int = 4) -> str:
    """Return annotated diff lines near ``finding.line`` in ``finding.path``.

    Returns up to ``2 * radius + 1`` lines centred on the finding's line,
    taken from the file's section of the unified diff.  Falls back to an
    empty string when the file is not found in the diff.
    """
    if not diff_text or not finding.path:
        return ""

    from code_review.diff.parser import annotate_diff_with_line_numbers, parse_unified_diff
    from code_review.diff.utils import normalize_path

    norm_target = normalize_path(finding.path)

    # Find the hunk(s) for this file
    hunks = [h for h in parse_unified_diff(diff_text) if normalize_path(h.path) == norm_target]
    if not hunks:
        return ""

    # Re-annotate just this file's diff text
    # Reconstruct a mini per-file diff from the hunks' raw lines
    # We annotate the full diff and then filter to the relevant window
    annotated = annotate_diff_with_line_numbers(diff_text)

    target_line = finding.line
    window_lines: list[str] = []
    in_file = False

    for raw_line in annotated.splitlines():
        # Detect file boundary
        if raw_line.startswith("diff --git"):
            current_path = ""
            parts = raw_line.split(" b/", 1)
            if len(parts) == 2:
                current_path = normalize_path(parts[1].strip())
            in_file = current_path == norm_target
            continue

        if not in_file:
            continue

        # Check if this annotated line is within the radius window
        stripped = raw_line.lstrip()
        line_no: int | None = None
        if ":" in stripped:
            prefix = stripped.split(":", 1)[0]
            if prefix.isdigit():
                line_no = int(prefix)

        if line_no is not None and abs(line_no - target_line) <= radius:
            window_lines.append(raw_line)
        elif line_no is not None and window_lines and line_no > target_line + radius:
            break  # past the window; stop collecting

    return "\n".join(window_lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_VERIFIABLE_CONFIDENCES: frozenset[str] = frozenset({"medium", "low"})


def verify_findings(
    findings: list[FindingV1],
    diff_text: str,
) -> list[FindingV1]:
    """Run a second-opinion verification pass for medium/low-confidence findings.

    High-confidence findings (and those without a confidence label) are returned
    unchanged.  Medium/low-confidence findings are sent to the verification agent
    in batches; only confirmed findings are kept.

    Returns a new list preserving the original order of high-confidence findings
    interleaved with confirmed lower-confidence ones.
    """
    if not findings:
        return findings

    high: list[tuple[int, FindingV1]] = []
    to_verify: list[tuple[int, FindingV1]] = []

    for idx, f in enumerate(findings):
        if f.confidence in _VERIFIABLE_CONFIDENCES:
            to_verify.append((idx, f))
        else:
            high.append((idx, f))

    if not to_verify:
        logger.info("Verification: all %d finding(s) have high/unset confidence; skipping", len(findings))
        return findings

    logger.info(
        "Verification: %d high/unset-confidence finding(s) pass through; "
        "%d medium/low-confidence finding(s) will be verified",
        len(high),
        len(to_verify),
    )

    confirmed: list[tuple[int, FindingV1]] = []
    total_confirmed = 0
    total_rejected = 0

    # Process in batches to keep prompts manageable
    for batch_start in range(0, len(to_verify), _MAX_FINDINGS_PER_BATCH):
        batch = to_verify[batch_start : batch_start + _MAX_FINDINGS_PER_BATCH]
        batch_confirmed, batch_rejected = _verify_batch(batch, diff_text)
        confirmed.extend(batch_confirmed)
        total_confirmed += len(batch_confirmed)
        total_rejected += batch_rejected

    logger.info(
        "Verification: confirmed=%d rejected=%d (of %d verified)",
        total_confirmed,
        total_rejected,
        len(to_verify),
    )

    # Merge high-confidence + confirmed, restoring original order
    merged: list[tuple[int, FindingV1]] = high + confirmed
    merged.sort(key=lambda t: t[0])
    return [f for _, f in merged]


def _verify_batch(
    batch: list[tuple[int, FindingV1]],
    diff_text: str,
) -> tuple[list[tuple[int, FindingV1]], int]:
    """Verify one batch of findings.  Returns (confirmed_list, rejected_count)."""
    prompt = _build_verification_prompt(batch, diff_text)
    result = _run_verification_agent(prompt)

    if result is None:
        # On failure, keep all findings (fail open)
        logger.warning(
            "Verification agent failed for batch of %d finding(s); keeping all as-is",
            len(batch),
        )
        return list(batch), 0

    verdict_by_index: dict[int, _VerificationVerdict] = {v.index: v for v in result.verdicts}

    confirmed: list[tuple[int, FindingV1]] = []
    rejected = 0

    for local_idx, (original_idx, finding) in enumerate(batch):
        verdict = verdict_by_index.get(local_idx)
        if verdict is None:
            # Agent omitted this finding — treat as confirmed (fail open)
            logger.debug(
                "Verification: no verdict for finding %s:%d — keeping (fail-open)",
                finding.path,
                finding.line,
            )
            confirmed.append((original_idx, finding))
        elif verdict.verdict == "confirm":
            logger.debug(
                "Verification: confirmed %s:%d — %s",
                finding.path,
                finding.line,
                verdict.reason,
            )
            confirmed.append((original_idx, finding))
        else:
            logger.info(
                "Verification: rejected %s:%d (%s) — %s",
                finding.path,
                finding.line,
                finding.code,
                verdict.reason,
            )
            rejected += 1

    return confirmed, rejected


def _build_verification_prompt(
    batch: list[tuple[int, FindingV1]],
    diff_text: str,
) -> str:
    """Build the user message for one verification batch."""
    blocks: list[str] = [f"Verify the following {len(batch)} finding(s):\n"]
    for local_idx, (_, finding) in enumerate(batch):
        snippet = _extract_snippet_for_finding(finding, diff_text)
        block = (
            f"--- Finding {local_idx} ---\n"
            f"index: {local_idx}\n"
            f"file: {finding.path}\n"
            f"line: {finding.line}\n"
            f"message: {finding.message}\n"
            f"evidence: {finding.evidence or '(none provided)'}\n"
            f"code_snippet:\n{snippet or '(not available)'}\n"
        )
        blocks.append(block)
    return "\n".join(blocks)


def _run_verification_agent(prompt: str) -> _VerificationResult | None:
    """Invoke the verification agent and return the parsed result, or None on error."""
    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        agent = create_verification_agent()
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name="code_review",
            session_service=session_service,
            auto_create_session=True,
        )
        content = types.Content(role="user", parts=[types.Part(text=prompt)])

        # Collect the structured output from the agent's last response
        raw_response: str = ""
        for event in runner.run(session_id="verification_session", input_=content):
            # ADK yields events; the final agent response carries the structured output text
            candidate = getattr(event, "content", None)
            if candidate is None:
                continue
            parts = getattr(candidate, "parts", None) or []
            for part in parts:
                text = getattr(part, "text", None)
                if text:
                    raw_response = text  # last text wins

        if not raw_response.strip():
            logger.warning("Verification agent returned empty response")
            return None

        return _parse_verification_result(raw_response)

    except Exception as exc:
        logger.warning("Verification agent invocation failed: %s", exc, exc_info=True)
        return None


def _parse_verification_result(text: str) -> _VerificationResult | None:
    """Parse the agent's JSON text into a _VerificationResult, or None on failure."""
    import json

    from code_review.json_utils import iter_json_candidates

    for candidate in iter_json_candidates(text):
        try:
            data = json.loads(candidate)
            return _VerificationResult.model_validate(data)
        except Exception:
            continue

    logger.warning("Could not parse verification result from: %.200s", text)
    return None
