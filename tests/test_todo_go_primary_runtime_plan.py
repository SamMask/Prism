from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TODO_PATH = ROOT / "docs" / "TODO.md"
GO_COMPLETION_PATH = (
    ROOT
    / "docs"
    / "development-history"
    / "go-primary-runtime-completion-20260617.md"
)
ARCHIVE_PATH = (
    ROOT
    / "docs"
    / "development-history"
    / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
)
CONTRACTS_PATH = ROOT / "docs" / "CONTRACTS.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"


EXPECTED_HEADER = "| ID | 任務 | 依賴 | 契約 | 結構依據 | 驗收標準 | 狀態 |"
ALLOWED_STATUS = {"Todo", "Doing", "Blocked", "Review", "Done"}


def _todo_rows():
    rows = []
    for line in GO_COMPLETION_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("| T"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            rows.append(cells)
    return rows


def test_active_todo_uses_required_table_shape():
    text = GO_COMPLETION_PATH.read_text(encoding="utf-8")

    assert EXPECTED_HEADER in text

    rows = _todo_rows()
    assert rows
    for row in rows:
        assert len(row) == 7
        assert row[0].startswith("T")
        assert row[1]
        assert row[2]
        assert row[3].startswith("CONTRACT-")
        assert row[4]
        assert row[5]
        assert row[6] in ALLOWED_STATUS


def test_legacy_todo_was_archived_instead_of_lost():
    archive_text = ARCHIVE_PATH.read_text(encoding="utf-8")
    active_text = TODO_PATH.read_text(encoding="utf-8")

    assert "# Prism - Modernization & Intelligence Roadmap (TODO)" in archive_text
    assert "completed_no_deletion_retained_python_package" in archive_text
    assert "A-E 已經跑完" in archive_text
    assert "completed_no_deletion_retained_python_package" not in active_text
    assert "23.8-thumb" not in active_text


def test_todo_contracts_are_defined():
    contracts_text = CONTRACTS_PATH.read_text(encoding="utf-8")
    contracts = {row[3] for row in _todo_rows()}

    assert contracts
    for contract in sorted(contracts):
        assert contract in contracts_text


def test_todo_structure_references_exist():
    architecture_text = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    rows = _todo_rows()

    assert "## Go Primary Runtime Migration Target" in architecture_text
    for arch_id in {
        "ARCH-GO-PRIMARY-00",
        "ARCH-GO-PRIMARY-01",
        "ARCH-GO-PRIMARY-02",
        "ARCH-GO-PRIMARY-03",
        "ARCH-GO-PRIMARY-04",
        "ARCH-GO-PRIMARY-05",
        "ARCH-GO-PRIMARY-06",
        "ARCH-GO-PRIMARY-07",
        "ARCH-GO-PRIMARY-08",
        "ARCH-GO-PRIMARY-09",
        "ARCH-GO-PRIMARY-10",
    }:
        assert arch_id in architecture_text

    for row in rows:
        assert "ARCH-GO-PRIMARY-" in row[4] or "SCHEMA:" in row[4]


def test_go_replacement_plan_covers_python_owned_runtime_surfaces():
    text = GO_COMPLETION_PATH.read_text(encoding="utf-8")

    required_terms = [
        "route ownership manifest",
        "fresh DB init",
        "migration runner",
        "notes create/update",
        "notes delete",
        "categories create/update/delete",
        "tags create/update/delete/merge",
        "attachments metadata",
        "attachment raw/text/binary",
        "POST /api/upload",
        "thumbnail generation",
        "POST /api/upload/url",
        "upload delete",
        "orphan images",
        "originals cleanup",
        "broken images",
        "Markdown import",
        "JSON import",
        "JSON/Markdown export",
        "DB/images export",
        "server version/status/hardware/logs",
        "backup list/create/download/delete/rotate",
        "port/config/service availability",
        "embedded SPA",
        "security parity",
        "full workflow E2E",
        "Windows package smoke",
        "linux/arm64 package smoke",
        "Pi staging Go primary unit",
        "Pi live Go primary cutover",
        "rollback drill",
        "Go primary soak window",
        "Python packaged runtime",
    ]

    for term in required_terms:
        assert term in text
