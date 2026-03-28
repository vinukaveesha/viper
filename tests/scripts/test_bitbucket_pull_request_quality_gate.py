from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bitbucket_pull_request_quality_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("bitbucket_pull_request_quality_gate", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_comment_report_marks_orphaned_comment_not_counted() -> None:
    module = load_module()

    report = module.build_comment_report(
        {
            "id": 42,
            "text": "[High] already applied",
            "state": "OPEN",
            "anchor": {"path": "src/Foo.java", "line": 5, "orphaned": True},
        }
    )

    assert report["comment_id"] == "42"
    assert report["counts_for_quality_gate"] is False
    assert report["quality_gate_reason"] == "outdated_or_orphaned"
    assert report["inferred_severity"] == "high"


def test_build_pr_gate_report_counts_only_open_high_medium(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()

    monkeypatch.setattr(
        module,
        "list_pull_request_comments",
        lambda *args, **kwargs: [
            {
                "id": 1,
                "text": "[High] still blocking",
                "state": "OPEN",
                "anchor": {"path": "src/Foo.java", "line": 5},
            },
            {
                "id": 2,
                "text": "[Medium] applied suggestion",
                "state": "OPEN",
                "anchor": {"path": "src/Foo.java", "line": 8, "orphaned": True},
            },
        ],
    )
    monkeypatch.setattr(
        module,
        "list_pull_request_tasks",
        lambda *args, **kwargs: [
            {"id": 9, "state": "OPEN", "text": "[Medium] task body"},
            {"id": 10, "state": "RESOLVED", "text": "[High] old task"},
        ],
    )

    report = module.build_pr_gate_report(
        "PRJ",
        "demo-repo",
        17,
        username="alice",
        password="secret",
    )

    assert report["open_high_count"] == 1
    assert report["open_medium_count"] == 1
    assert [item["kind"] for item in report["counted_items"]] == ["comment", "task"]


def test_main_comment_prints_json_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_module()

    monkeypatch.setattr(module, "load_script_credentials", lambda: ("alice", "secret"))
    monkeypatch.setattr(
        module,
        "get_pull_request_comment",
        lambda *args, **kwargs: {
            "id": 42,
            "text": "[High] applied suggestion",
            "state": "OPEN",
            "anchor": {"path": "src/Foo.java", "line": 5, "orphaned": True},
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bitbucket_pull_request_quality_gate.py",
            "comment",
            "PRJ",
            "demo-repo",
            "17",
            "42",
        ],
    )

    assert module.main() == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["comment_id"] == "42"
    assert payload["counts_for_quality_gate"] is False
    assert payload["quality_gate_reason"] == "outdated_or_orphaned"
