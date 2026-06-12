import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"
CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-sqlite-connection-owner.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
README_PATH = GO_SHADOW_DIR / "README.md"


def _load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_t007_contract_records_sqlite_owner_boundary():
    contract = _load_contract()

    assert contract["task_id"] == "T007"
    assert contract["status"] == "completed"
    assert contract["source_manifest"] == "docs/contracts/go-primary-runtime-config-data-dir.json"
    assert contract["sqlite_owner"]["journal_mode"] == "WAL"
    assert contract["sqlite_owner"]["busy_timeout_ms"] == 5000
    assert contract["sqlite_owner"]["dsn_pragmas_apply_to_each_connection"] is True
    assert contract["write_mode_switch"]["default_query_only"] is True
    assert "--enable-tag-write" in contract["write_mode_switch"]["db_write_flags"]
    assert "--enable-thumbnail-write" in contract["write_mode_switch"]["file_write_flags_keep_db_read_only"]
    assert contract["transaction_helper"]["commit_and_rollback_tested"] is True
    assert contract["transaction_helper"]["partial_write_blocked_on_error"] is True
    assert "Does not implement Go fresh DB init." in contract["boundaries"]
    assert "Does not touch production DB/files." in contract["boundaries"]


def test_t007_go_source_and_unit_tests_lock_owner_behavior():
    main_go = (GO_SHADOW_DIR / "main.go").read_text(encoding="utf-8")
    go_tests = (GO_SHADOW_DIR / "main_test.go").read_text(encoding="utf-8")

    for snippet in (
        "type sqliteConnectionOwner struct",
        "func openSQLiteOwner",
        "func sqliteDSN",
        "url.Values{}",
        "_pragma",
        "PRAGMA busy_timeout",
        "journal_mode(WAL)",
        "PRAGMA query_only = ON",
        "PRAGMA query_only = OFF",
        "func (owner *sqliteConnectionOwner) withTransaction",
        "SQLite write transaction requires write mode",
        "openRuntimeSQLite(&cfg)",
    ):
        assert snippet in main_go

    for test_name in (
        "TestSQLiteOwnerDSNConfiguresPragmasForEachConnection",
        "TestSQLiteOwnerConfiguresWALBusyTimeoutAndReadOnlyMode",
        "TestSQLiteOwnerWriteModeTransactionCommitAndRollback",
    ):
        assert test_name in go_tests
    assert "assertSQLiteOwnerSettings" in go_tests
    assert "assertTagCount(t, owner.db, \"committed\", 1)" in go_tests
    assert "assertTagCount(t, owner.db, \"rolled_back\", 0)" in go_tests


def test_t007_docs_mark_done_and_keep_runtime_boundaries():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")

    row = next(line for line in todo.splitlines() if line.startswith("| T007 "))
    assert row.endswith("| Done |")
    assert "go-primary-sqlite-connection-owner.json" in row
    assert "T007 SQLite connection owner gate 已完成" in todo

    assert "T007 SQLite connection owner gate is complete" in architecture
    assert "WAL, 5000 ms busy timeout" in architecture
    assert "modernc `_pragma` DSN" in architecture
    assert "does not implement fresh DB init" in architecture
    assert "does not promote live Go ownership" in architecture

    assert "SQLite connection owner" in readme
    assert "modernc `_pragma` DSN" in readme
    assert "busy_timeout = 5000" in readme
    assert "query_only = ON" in readme
