import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TODO_PATH = ROOT / "docs" / "development-history" / "go-primary-runtime-completion-20260617.md"
AGENTS_PATH = ROOT / "AGENTS.md"
CLAUDE_PATH = ROOT / "CLAUDE.md"
INDEX_PATH = ROOT / "docs" / "INDEX.md"
HISTORY_README_PATH = ROOT / "docs" / "development-history" / "README.md"
CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-python-packaged-runtime-deletion.json"
ROUTE_COVERAGE_CONTRACT_PATH = (
    ROOT / "docs" / "contracts" / "go-primary-frontend-route-coverage.json"
)
ROOT_GO_REPORT_PATH = ROOT / "Prism_Go_\u6a21\u7d44\u9010\u6b65\u91cd\u69cb\u8a08\u5283\u5831\u544a.md"
ARCHIVED_GO_REPORT_PATH = (
    ROOT
    / "docs"
    / "development-history"
    / "Prism_Go_\u6a21\u7d44\u9010\u6b65\u91cd\u69cb\u8a08\u5283\u5831\u544a.md"
)
ROOT_GO_CLOSURE_AUDIT_PATH = ROOT / "Go\u91cd\u69cb\u5be9\u67e5\u5831\u544a-20260613-codex.md"
ARCHIVED_GO_CLOSURE_AUDIT_PATH = (
    ROOT
    / "docs"
    / "development-history"
    / "Go\u91cd\u69cb\u5be9\u67e5\u5831\u544a-20260613-codex.md"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _todo_row(task_id: str) -> str:
    return next(line for line in _text(TODO_PATH).splitlines() if line.startswith(f"| {task_id} "))


def test_go_roadmap_report_is_archived_not_root_current_truth():
    assert not ROOT_GO_REPORT_PATH.exists()
    assert ARCHIVED_GO_REPORT_PATH.exists()

    archived = _text(ARCHIVED_GO_REPORT_PATH)
    index = _text(INDEX_PATH)
    history_readme = _text(HISTORY_README_PATH)

    assert "\u6b77\u53f2\u5c01\u5b58" in archived
    assert "T046-T053 queue" in archived
    assert "docs/development-history/Prism_Go_\u6a21\u7d44\u9010\u6b65\u91cd\u69cb\u8a08\u5283\u5831\u544a.md" in _text(AGENTS_PATH)
    assert _text(AGENTS_PATH) == _text(CLAUDE_PATH)
    assert "./development-history/Prism_Go_\u6a21\u7d44\u9010\u6b65\u91cd\u69cb\u8a08\u5283\u5831\u544a.md" in index
    assert "Prism_Go_\u6a21\u7d44\u9010\u6b65\u91cd\u69cb\u8a08\u5283\u5831\u544a.md" in history_readme


def test_go_closure_audit_report_is_archived_and_discoverable_after_t046_t052():
    assert not ROOT_GO_CLOSURE_AUDIT_PATH.exists()
    assert ARCHIVED_GO_CLOSURE_AUDIT_PATH.exists()

    archived = _text(ARCHIVED_GO_CLOSURE_AUDIT_PATH)
    index = _text(INDEX_PATH)
    history_readme = _text(HISTORY_README_PATH)
    agents = _text(AGENTS_PATH)
    route_contract = json.loads(_text(ROUTE_COVERAGE_CONTRACT_PATH))

    assert "\u6b77\u53f2\u5c01\u5b58 / \u5df2\u5438\u6536" in archived
    assert "T046-T052" in archived
    assert "T053 Python backend source" in archived
    assert "docs/development-history/Go\u91cd\u69cb\u5be9\u67e5\u5831\u544a-20260613-codex.md" in agents
    assert "Go\u91cd\u69cb\u5be9\u67e5\u5831\u544a-20260613-codex.md" in index
    assert "Go\u91cd\u69cb\u5be9\u67e5\u5831\u544a-20260613-codex.md" in history_readme
    assert (
        route_contract["scope"]["review_basis"]
        == "docs/development-history/Go\u91cd\u69cb\u5be9\u67e5\u5831\u544a-20260613-codex.md"
    )
    assert _text(AGENTS_PATH) == _text(CLAUDE_PATH)


def test_t046_t053_queue_captures_confirmed_go_primary_audit_gaps():
    todo = _text(TODO_PATH)
    assert "T046-T050 \u5df2\u88dc\u9f4a 2026-06-13 Go \u6536\u5c3e\u5be9\u67e5\u5217\u51fa\u7684 frontend \u5be6\u969b\u547c\u53eb\u6f0f\u63a5 surface" in todo
    assert "T053 \u5df2\u5b8c\u6210 Python backend source \u7269\u7406\u522a\u9664\u8207 docs/API/release wording \u6536\u6582" in todo

    rows = {task_id: _todo_row(task_id) for task_id in [f"T{n:03d}" for n in range(46, 54)]}
    assert all(rows[task_id].endswith("| Done |") for task_id in [f"T{n:03d}" for n in range(46, 54)])

    assert "frontend \u2192 Go primary route coverage" in rows["T046"]
    assert "extract-prompt" in rows["T047"]
    assert "check_separation" in rows["T048"]
    assert "separate" in rows["T048"]
    assert "check-update" in rows["T049"]
    assert "wizard_options.json" in rows["T050"]
    assert "route ownership manifest" in rows["T051"]
    assert "API reference" in rows["T051"]
    assert "resources/python-embed.zip" in rows["T052"]
    assert "pillow-12.0.0" in rows["T052"]
    assert "knowledge.db" in rows["T052"]
    assert "Python backend source" in rows["T053"]
    assert "T047, T048, T049, T050, T051, T052" in rows["T053"]


def test_t045_contract_hands_off_to_route_audit_before_final_source_cleanup():
    contract = json.loads(_text(CONTRACT_PATH))

    assert contract["next_recommended_task"]["id"] == "T046"
    assert "frontend-to-Go route coverage" in contract["next_recommended_task"]["reason"]
    assert contract["final_source_deletion_task"]["id"] == "T053"
    assert "Final Python backend source archival/deletion" in contract["final_source_deletion_task"]["reason"]
