import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = ROOT / "docs" / "contracts" / "phase21-local-commit-push-readiness.json"
TODO_PATH = ROOT / "docs" / "TODO.md"


def _readiness():
    return json.loads(READINESS_PATH.read_text(encoding="utf-8"))


def test_phase21_1_records_authorized_plan_only_local_commit_push_branch():
    readiness = _readiness()

    assert readiness["phase"] == "21.1"
    assert readiness["explicit_user_approval"] is True
    assert readiness["plan_only"] is True
    assert readiness["selected_branch"] == "local_commit_push"
    assert readiness["runtime_change_performed"] is False
    assert readiness["live_pi_change_performed"] is False
    assert readiness["caddy_change_performed"] is False
    assert readiness["frontend_default_change_performed"] is False
    assert readiness["git_commit_performed"] is False
    assert readiness["git_push_performed"] is False


def test_phase21_1_locks_dirty_tree_and_privacy_sweep_evidence():
    readiness = _readiness()
    evidence = readiness["sweep_evidence"]

    assert evidence["git_status_short_branch"] == "## main...origin/main"
    assert evidence["head_origin_divergence"] == "0 0"
    assert evidence["tracked_diff_before_21_1"] == "none"
    assert evidence["untracked_non_ignored_before_21_1"] == "none"
    assert evidence["live_pi_verified"] is False
    assert evidence["privacy_artifacts_tracked"] == []

    ignored = set(evidence["privacy_artifacts_observed_ignored"])
    assert "knowledge.db" in ignored
    assert "app.log" in ignored
    assert "static/uploads/" in ignored
    assert "docs/attachments/" in ignored


def test_phase21_1_commit_scope_is_docs_and_tests_only():
    readiness = _readiness()
    groups = {group["id"]: group for group in readiness["proposed_commit_grouping"]}
    group = groups["phase21_local_commit_push_readiness"]

    assert group["include"] == [
        "docs/contracts/phase21-local-commit-push-readiness.json",
        "tests/test_phase21_local_commit_push_readiness.py",
        "docs/TODO.md",
    ]

    excluded = " ".join(group["exclude"])
    assert "knowledge.db" in excluded
    assert "static/uploads/" in excluded
    assert "docs/attachments/" in excluded
    assert ".env*" in excluded


def test_phase21_1_forbids_commit_push_deploy_and_go_scope_expansion():
    readiness = _readiness()
    forbidden = readiness["not_authorized_by_21_1"]

    assert "Git commit" in forbidden
    assert "Git push" in forbidden
    assert "Pi deploy" in forbidden
    assert "Caddy reload or route expansion" in forbidden
    assert "Go attachment file body scanning" in forbidden
    assert "Go write/file/migration implementation" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Python backend removal" in forbidden
    assert "Direct public internet exposure" in forbidden


def test_phase21_1_next_step_is_explicit_21_2_commit_push_approval_gate():
    readiness = _readiness()
    next_step = readiness["allowed_next_step"]

    assert next_step["id"] == "21.2"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert next_step["scope"].startswith("After 21.1 validation")
    assert "git add" in next_step["not_authorized_without_approval"]
    assert "git commit" in next_step["not_authorized_without_approval"]
    assert "git push" in next_step["not_authorized_without_approval"]


def test_phase21_1_todo_records_readiness_gate_and_next_approval_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "21.1 Local Commit and Push Readiness Gate" in todo
    assert "docs/contracts/phase21-local-commit-push-readiness.json" in todo
    assert "21.2 Explicit Local Commit and Push Approval Gate" in todo
    assert "未做 git commit/push" in todo
