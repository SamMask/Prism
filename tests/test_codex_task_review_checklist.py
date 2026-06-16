from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKLIST_PATH = ROOT / "docs" / "CODEX-TASK-REVIEW-CHECKLIST.md"
TODO_PATH = ROOT / "docs" / "TODO.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_codex_task_review_checklist_exists_and_keeps_prompt_contract():
    text = _text(CHECKLIST_PATH)

    for phrase in (
        "任務目標",
        "背景",
        "允許修改檔案",
        "禁止事項",
        "具體要求",
        "驗收指令",
        "回報格式",
    ):
        assert phrase in text

    assert "### Changed" in text
    assert "### Verified" in text
    assert "### Not Changed" in text
    assert "No API changes." in text
    assert "No schema changes." in text
    assert "No backend changes." in text
    assert "No unrelated feature work." in text


def test_codex_task_review_checklist_locks_scope_and_hard_return_terms():
    text = _text(CHECKLIST_PATH)

    for phrase in (
        "Allowed Files",
        "Forbidden Scope",
        "Verification Checklist",
        "Reviewer Checklist",
        "Hard Return Conditions",
        "schema",
        "migration",
        "API contract",
        "AI",
        "embedding",
        "semantic search",
        "GraphRAG",
        "runtime",
        "deploy",
        "Pi service",
        "Caddy",
        "無關重構",
        "PortConfigSection",
        "UpdateSection",
        "部署安全邊界",
    ):
        assert phrase in text

    assert "不修改 agent runtime" in text
    assert "不取代 repo canonical docs" in text
    assert "不得宣稱完成" in text


def test_codex_review_01_todo_is_closed_with_docs_only_boundary():
    todo = _text(TODO_PATH)

    assert "[x] **CODEX-REVIEW-01 Codex task/review checklist extraction**" in todo
    assert "docs/CODEX-TASK-REVIEW-CHECKLIST.md" in todo
    assert "不改 agent runtime" in todo
    assert "不改 `AGENTS.md` / `CLAUDE.md`" in todo
