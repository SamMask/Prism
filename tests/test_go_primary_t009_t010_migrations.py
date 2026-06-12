import json
import os
import shutil
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tests.go_primary_parity_harness import build_go_shadow_exe


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"
T009_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-existing-db-migration-runner.json"
T010_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-migration-backup-rollback.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
README_PATH = GO_SHADOW_DIR / "README.md"


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_json(url, timeout=30):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(0.25)
    raise AssertionError(f"{url} did not become ready: {last_error}")


def _create_legacy_db(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE Categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                icon TEXT DEFAULT '📝',
                sort_order INTEGER DEFAULT 0,
                is_default INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE Notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                type TEXT DEFAULT '筆記',
                remarks TEXT,
                cover_image TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE Tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE Note_Tags (
                note_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (note_id, tag_id)
            );
            CREATE TABLE Source_Urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER,
                url TEXT
            );
            CREATE TABLE Note_History (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER,
                content TEXT,
                diff_summary TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE VIRTUAL TABLE Notes_FTS USING fts5(
                title, content,
                content='Notes',
                content_rowid='id'
            );
            INSERT INTO Categories (name, icon, is_default) VALUES ('筆記', '📝', 1);
            INSERT INTO Notes (title, content, type) VALUES ('Legacy Note', 'legacy body', '筆記');
            """
        )


def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_t009_t010_contracts_record_migration_and_rollback_scope():
    t009 = _load_json(T009_CONTRACT_PATH)
    t010 = _load_json(T010_CONTRACT_PATH)

    assert t009["task_id"] == "T009"
    assert t009["status"] == "completed"
    assert t009["allowed_scope"]["existing_db_upgrade"] is True
    assert t009["allowed_scope"]["ordered_python_migration_parity"] is True
    assert t009["allowed_scope"]["idempotent_duplicate_column_skip"] is True
    assert t009["allowed_scope"]["idempotent_missing_column_skip"] is True
    assert t009["implementation"]["ordered_versions"] == list(range(1, 17))
    assert "Production knowledge.db migration without explicit env override" in t009["not_in_scope"]

    assert t010["task_id"] == "T010"
    assert t010["status"] == "completed"
    assert t010["allowed_scope"]["backup_before_migrate"] is True
    assert t010["allowed_scope"]["failed_migration_rollback"] is True
    assert t010["allowed_scope"]["schema_meta_not_advanced_on_failure"] is True
    assert t010["allowed_scope"]["startup_aborts_on_migration_failure"] is True
    assert t010["next_task"]["id"] == "T011"


def test_t009_t010_go_source_and_unit_tests_lock_runner_backup_and_rollback():
    main_go = (GO_SHADOW_DIR / "main.go").read_text(encoding="utf-8")
    go_tests = (GO_SHADOW_DIR / "main_test.go").read_text(encoding="utf-8")

    for snippet in (
        "func runExistingDBMigrations",
        "func backupSQLiteBeforeMigration",
        "func migrationStatus",
        "func detectExistingSchemaVersion",
        "duplicate column name",
        "no such column",
        "UPDATE Schema_Meta SET value = ?",
        "ALTER TABLE Notes ADD COLUMN is_pinned",
        "ALTER TABLE Notes DROP COLUMN type",
        "DROP TABLE IF EXISTS AI_Tasks",
        "migration failed after backup",
        '"migrations_applied":',
        '"migration_backup_path":',
    ):
        assert snippet in main_go

    for test_name in (
        "TestOpenRuntimeSQLiteMigratesLegacyDBCreatesBackupAndReturnsReadOnlyOwner",
        "TestRunExistingDBMigrationsSkipsDuplicateAndMissingColumns",
        "TestOpenRuntimeSQLiteFailedMigrationRollsBackAndKeepsBackup",
    ):
        assert test_name in go_tests


def test_t009_go_runtime_migrates_existing_legacy_db_and_creates_backup(tmp_path):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; source/contract tests still run.")

    data_dir = tmp_path / "data"
    db_path = data_dir / "legacy_runtime_dev.db"
    _create_legacy_db(db_path)
    port = _free_port()
    exe_path = build_go_shadow_exe(go_bin, tmp_path)
    proc = subprocess.Popen(
        [
            str(exe_path),
            "--db",
            "legacy_runtime_dev.db",
            "--addr",
            f"127.0.0.1:{port}",
            "--data-dir",
            str(data_dir),
        ],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        try:
            status, health = _wait_for_json(base + "/healthz")
        except Exception as exc:
            proc.terminate()
            output, _ = proc.communicate(timeout=5)
            raise AssertionError(output) from exc

        assert status == 200
        runtime = health["runtime"]
        assert runtime["schema_version"] == 16
        assert runtime["expected_schema_version"] == 16
        assert runtime["sqlite_query_only"] is True
        assert runtime["migrations_applied"] > 0
        backup_path = Path(runtime["migration_backup_path"])
        assert backup_path.exists()
        assert backup_path.parent == data_dir / "backups"

        status_code, migration_status = _wait_for_json(base + "/api/system/migration-status")
        assert status_code == 200
        assert migration_status["data"]["current_version"] == 16
        assert migration_status["data"]["latest_version"] == 16
        assert migration_status["data"]["pending"] == []
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    with sqlite3.connect(db_path) as conn:
        note_columns = _columns(conn, "Notes")
        assert "type" not in note_columns
        assert "prompt_params" in note_columns
        assert "parent_id" in note_columns
        assert "text_embedding" not in note_columns
        version = conn.execute("SELECT value FROM Schema_Meta WHERE key='schema_version'").fetchone()[0]
        assert version == "16"

    with sqlite3.connect(backup_path) as conn:
        assert "type" in _columns(conn, "Notes")
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("SELECT value FROM Schema_Meta WHERE key='schema_version'").fetchone()


def test_t009_t010_docs_mark_done_and_keep_scope_boundaries():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")

    row_t009 = next(line for line in todo.splitlines() if line.startswith("| T009 "))
    row_t010 = next(line for line in todo.splitlines() if line.startswith("| T010 "))
    assert row_t009.endswith("| Done |")
    assert row_t010.endswith("| Done |")
    assert "go-primary-existing-db-migration-runner.json" in row_t009
    assert "go-primary-migration-backup-rollback.json" in row_t010
    assert "T009/T010 Go migration runner safety gate 已完成" in todo
    assert "未部署 Pi" in todo

    assert "T009/T010 Go migration runner safety gate is complete" in architecture
    assert "backup-before-migrate" in architecture
    assert "does not touch production `knowledge.db`" in architecture

    assert "Go T009/T010" in schema
    assert "Existing DB Migrations" in readme
    assert "backup-before-migrate" in readme
