# Architectural Refactor Checklist

This checklist tracks the implementation of the [Architectural Refactor Plan](ARCHITECTURAL-REFACTOR-PLAN.md).

## Phase 1: Foundation (Logic Extraction)
- [ ] Create `src/code_review/diff/analyzer.py` and migrate `_estimate_tokens`, `_normalize_path_for_anchor`.
- [ ] Create `src/code_review/refinement/` package and migrate `_relocate_findings_by_anchor`, `_filter_self_retracted_finding_messages`.
- [ ] Create `src/code_review/diff/line_index.py` and migrate `_build_diff_line_index`.
- [ ] Verify: Run `pytest tests/diff/` and `pytest tests/agent/`.

## Phase 2: State Delegation (Manager Implementation)
- [ ] Create `src/code_review/comments/manager.py`.
- [ ] Implement `CommentManager.load_existing_comments()` using logic from `_load_existing_comments_and_markers`.
- [ ] Implement `CommentManager.filter_duplicates()` using logic from `_attach_fingerprints_and_filter_findings`.
- [ ] Create `src/code_review/quality/gate.py` and migrate `_compute_quality_gate_review_outcome`.
- [ ] Verify: Run `pytest tests/runner/test_idempotency.py` and `pytest tests/runner/test_orchestrator.py`.

## Phase 3: Orchestrator Refactor
- [ ] Update `ReviewOrchestrator.run()` to instantiate used classes (`DiffAnalyzer`, `CommentManager`).
- [ ] Delegate PR filtering (skip labels/titles) to a new `ReviewFilter` in `src/code_review/orchestration/filter.py`.
- [ ] Delegate post-processing to `FindingRefinementPipeline`.
- [ ] Verify: Run all runner and integration tests.

## Phase 4: Finalization
- [ ] Remove `src/code_review/orchestration_deps.py`.
- [ ] Update all remaining imports in `src/code_review/runner.py`.
- [ ] Final full test pass including E2E (if possible).
- [ ] Update `docs/DEVELOPER_GUIDE.md` to reflect the new architecture.
