# Architectural Refactor Plan: De-godding the Review Orchestration

This document outines a comprehensive plan to refactor the code-review-agent's orchestration layer using Object-Oriented Programming (OOP) principles. The goal is to decompose the current "god files" (`orchestration_deps.py` and `ReviewOrchestrator.py`) into focused, maintainable, and testable components.

## 1. Problem Statement

The recent refactor of `runner.py` successfully moved logic out of the main entry point but resulted in two new "god files":
- **`ReviewOrchestrator.py` (~1,500 lines)**: Handles PR info fetching, file listing, language detection, batching, agent execution, and result collection.
- **`orchestration_deps.py` (~1,800 lines)**: A procedural "dumping ground" for 50+ helper functions covering diff parsing, comment posting, quality gates, and post-processing.

This creates high cognitive load, makes unit testing difficult, and hinders the extensibility of the system.

## 2. Target Architecture (OOP Design)

We will introduce a set of domain-specific classes to replace procedural helpers.

### 2.1 `DiffAnalyzer`
**Responsibility**: All operations on unified diffs and file content.
**Key Methods**:
- `analyze_pr_diff(diff_text)`: Builds internal line indexes and visible line sets.
- `estimate_tokens(content)`: Token budget estimation logic.
- `get_hunk_at(path, line)`: Retrieves context for a specific line.
- `normalize_path(path)`: Standardizes SCM-specific path prefixes.

### 2.2 `CommentManager`
**Responsibility**: Managing the lifecycle of review comments on the SCM.
**State**:
- `ignore_set`: Track existing comments to avoid duplicates.
- `resolved_fingerprints`: Track which findings have already been addressed.
**Key Methods**:
- `load_existing_comments(provider)`: Hydrates state from SCM.
- `filter_duplicates(findings)`: Uses fingerprints and hashes to deduplicate.
- `post_inline_comments(findings)`: Handles batch/individual posting logic.
- `resolve_stale_comments()`: Logic for auto-closing outdated threads.

### 2.3 `QualityGate`
**Responsibility**: Evaluating the overall review outcome against configuration.
**Key Methods**:
- `evaluate(findings)`: Returns a `QualityGateOutcome` (PASS/FAIL/WARNING).
- `submit_decision(provider, outcome)`: Translates outcome to SCM `APPROVE`/`REQUEST_CHANGES`.

### 2.4 `FindingRefinementPipeline`
**Responsibility**: Sanitizing and correcting LLM output via a series of filters.
**Filters**:
- `SelfRetractionFilter`: Removes findings where the LLM corrected itself in prose.
- `ContradictionFilter`: Drops findings directly contradicted by the diff context.
- `AnchorRelocator`: Corrects line numbers using anchor text fuzzy matching.
- `PatchValidator`: Strips suggested patches that don't match the target code.

## 3. Module Organization

New directory structure under `src/code_review/`:

```
src/code_review/
├── orchestration/          # New package for core review logic
│   ├── __init__.py
│   ├── orchestrator.py     # Simplified ReviewOrchestrator
│   └── execution.py        # Logic for running agents (ExecutionEngine)
├── diff/
│   ├── analyzer.py         # DiffAnalyzer class
│   └── (existing files)
├── comments/
│   ├── manager.py          # CommentManager class
│   └── (formatters etc)
├── quality/
│   ├── gate.py             # QualityGate class
│   └── outcome.py          # Value objects for results
└── refinement/
    ├── pipeline.py         # FindingRefinementPipeline
    └── filters/            # Individual filter implementations
```

## 4. Implementation Steps

The refactor will be executed in four phases to maintain system stability.

### Phase 1: Pure Logic Extraction (The "Foundation")
1. Move diff parsing and token estimation to `code_review.diff.analyzer`.
2. Move post-processing filters (relocation, retraction) to `code_review.refinement`.
3. Update `orchestration_deps.py` to simply import and re-export these for backward compatibility.

### Phase 2: State Delegation (The "Heart")
1. Implement `CommentManager` and move deduplication/fingerprinting logic into it.
2. Implement `QualityGate` and move the complex gating logic from `orchestration_deps.py`.

### Phase 3: Orchestrator Slimming
1. Refactor `ReviewOrchestrator` to use the new classes.
2. Remove private method bloat by delegating to `CommentManager` and `DiffAnalyzer`.

### Phase 4: Final Cleanup
1. Delete `orchestration_deps.py`.
2. Update all imports across the codebase (including tests).

## 5. Risk Mitigation

- **Test-Driven Refactor**: Every move must be followed by running the existing test suite (`pytest`).
- **Incremental Rollout**: Use the temporary re-exports in `orchestration_deps.py` to avoid breaking `ReviewOrchestrator` while its dependencies are moving.
