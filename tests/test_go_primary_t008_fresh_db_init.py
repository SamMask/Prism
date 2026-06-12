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
CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-fresh-db-init.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
README_PATH = GO_SHADOW_DIR / "README.md"


def _load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


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


def test_t008_contract_records_fresh_init_scope_and_boundaries():
    contract = _load_contract()

    assert contract["task_id"] == "T008"
    assert contract["status"] == "completed"
    assert contract["contract"] == "CONTRACT-GO-PRIMARY-MIGRATIONS"
    assert contract["allowed_scope"]["fresh_db_only"] is True
    assert contract["allowed_scope"]["schema_version"] == 16
    assert contract["allowed_scope"]["creates_current_schema"] is True
    assert contract["allowed_scope"]["creates_fts5_table_and_triggers"] is True
    assert contract["allowed_scope"]["returns_to_query_only_after_init"] is True
    assert contract["runtime_guards"]["missing_absolute_db_outside_data_dir_rejected"] is True
    assert contract["runtime_guards"]["production_named_knowledge_db_still_rejected_by_default"] is True
    assert "Existing DB migration runner" in contract["not_in_scope"]
    assert "Production knowledge.db writes" in contract["not_in_scope"]
    assert contract["next_task"]["id"] == "T009"


def test_t008_go_source_locks_fresh_init_entrypoint_after_later_migration_gates():
    main_go = (GO_SHADOW_DIR / "main.go").read_text(encoding="utf-8")
    go_tests = (GO_SHADOW_DIR / "main_test.go").read_text(encoding="utf-8")

    for snippet in (
        "freshDBInitNeeded",
        "func openRuntimeSQLite",
        "func initializeFreshDatabase",
        "freshSchemaStatements",
        "CREATE TABLE Schema_Meta",
        "INSERT INTO Schema_Meta (key, value) VALUES ('schema_version', '16')",
        "CREATE VIRTUAL TABLE Notes_FTS",
        "CREATE TRIGGER notes_ai",
        "seedDefaultCategories",
        "seedWelcomeNote",
        '"fresh_db_initialized":',
    ):
        assert snippet in main_go

    for test_name in (
        "TestRuntimeConfigMarksMissingRelativeDBForFreshInit",
        "TestRuntimeConfigRejectsMissingAbsoluteDBOutsideDataDir",
        "TestOpenRuntimeSQLiteInitializesFreshDBAndReturnsReadOnlyOwner",
    ):
        assert test_name in go_tests


def test_t008_fresh_go_runtime_creates_current_schema_from_empty_data_dir(tmp_path):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; source/contract tests still run.")

    data_dir = tmp_path / "data"
    db_rel = "fresh/prism_runtime_dev.db"
    db_path = data_dir / "fresh" / "prism_runtime_dev.db"
    port = _free_port()
    exe_path = build_go_shadow_exe(go_bin, tmp_path)
    proc = subprocess.Popen(
        [
            str(exe_path),
            "--db",
            db_rel,
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
        assert runtime["fresh_db_initialized"] is True
        assert runtime["sqlite_query_only"] is True
        assert Path(runtime["db_path"]) == db_path
        assert db_path.exists()

        categories_status, categories = _wait_for_json(base + "/api/categories")
        assert categories_status == 200
        assert [item["name"] for item in categories["data"]] == [
            "提示詞 | Prompt",
            "筆記 | Note",
            "教學 | Tutorial",
            "資料 | Data",
            "靈感 | Inspiration",
        ]
        assert next(item for item in categories["data"] if item["name"] == "筆記 | Note")["is_default"] is True

        test_status, test_body = _wait_for_json(base + "/api/test")
        assert test_status == 200
        assert test_body["stats"]["categories_count"] == 5
        assert test_body["stats"]["tags_count"] == 1
        assert test_body["stats"]["notes_count"] == 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    with sqlite3.connect(db_path) as conn:
        version = conn.execute("SELECT value FROM Schema_Meta WHERE key = 'schema_version'").fetchone()[0]
        assert version == "16"

        note_columns = {row[1]: row[4] for row in conn.execute("PRAGMA table_info(Notes)")}
        assert note_columns["editor_layout"] == "'single'"
        assert "parent_id" in note_columns
        assert "prompt_params" in note_columns
        assert "type" not in note_columns

        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND name LIKE 'idx_%'"
            )
        }
        assert {
            "idx_notes_updated_at",
            "idx_notes_category_id",
            "idx_notes_sort_order",
            "idx_notes_is_archived",
            "idx_notes_parent_id",
            "idx_tags_name",
            "idx_source_urls_note_id",
            "idx_note_history_note_id",
            "idx_attachments_note_id",
        } <= indexes

        triggers = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")
        }
        assert {"notes_ai", "notes_ad", "notes_au"} <= triggers

        fts_hits = conn.execute(
            "SELECT COUNT(*) FROM Notes_FTS WHERE Notes_FTS MATCH ?",
            ("Prism",),
        ).fetchone()[0]
        assert fts_hits == 1


def test_t008_docs_mark_done_and_keep_scope_boundaries():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")

    row = next(line for line in todo.splitlines() if line.startswith("| T008 "))
    assert row.endswith("| Done |")
    assert "go-primary-fresh-db-init.json" in row
    assert "T008 Go fresh DB init 已完成" in todo
    assert "未實作 existing DB migration runner" in todo

    assert "T008 Go fresh DB init is complete" in architecture
    assert "fresh DB only" in architecture
    assert "does not implement existing DB migration runner" in architecture
    assert "does not touch production `knowledge.db`" in architecture

    assert "Fresh DB Init" in readme
    assert "fresh/prism_runtime_dev.db" in readme
    assert "Existing DB migrations remain outside this gate" in readme
