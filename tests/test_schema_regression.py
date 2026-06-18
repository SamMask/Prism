# -*- coding: utf-8 -*-
"""Schema Regression Test — Go-sourced schema truth (T053 Gate 3 REWIRE).

Originally this guarded the Python fixture/migration chain
(`migrations.run_migrations` + `app.init_db`) as the authoritative schema.
After the Go primary cutover, the **Go runtime's fresh-init and existing-DB
migration output is the schema truth**, so this module now derives every
invariant from a real Go-created DB and imports **no** Python backend.

It therefore stays valid after T053 deletes `app.py` / `migrations/` / `db.py`.
A guard test below proves this module imports no Flask backend, so the schema
gate cannot silently regrow a Python dependency.

If a column is accidentally re-added, a DROP COLUMN migration is skipped, or the
v16 editor_layout normalization or v17 category identity regresses, these tests fail against the Go DB
before the regression reaches prod.
"""

import os
import re
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


# Authoritative final schema (Go `freshSchemaStatements`, go-shadow/main.go).
REQUIRED_NOTES_COLUMNS = {
    "id", "title", "content", "remarks", "cover_image", "cover_position",
    "editor_layout", "is_pinned", "is_archived", "sort_order", "category_id",
    "parent_id", "prompt_params", "created_at", "updated_at",
}

# Columns removed by migration v14 (AI strip); must never reappear.
STRIPPED_AI_COLUMNS = {
    "text_embedding", "embedding_updated_at", "ai_summary", "ai_tags",
    "embedding_status",
}

REQUIRED_CATEGORY_COLUMNS = {"system_key", "name_override"}


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_health(base, timeout=30):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=3) as response:
                import json

                return response.status, json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            time.sleep(0.25)
    raise AssertionError(f"{base}/healthz did not become ready: {last_error}")


def _boot_and_inspect(exe_path, data_dir, db_rel):
    """Boot the Go runtime once on data_dir/db_rel, wait until ready, stop.

    Returns the parsed /healthz `runtime` payload. The DB file persists at
    data_dir/db_rel for caller inspection.
    """
    port = _free_port()
    proc = subprocess.Popen(
        [
            str(exe_path),
            "--db", db_rel,
            "--addr", f"127.0.0.1:{port}",
            "--data-dir", str(data_dir),
        ],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        try:
            status, health = _wait_for_health(f"http://127.0.0.1:{port}")
        except Exception as exc:
            proc.terminate()
            output, _ = proc.communicate(timeout=5)
            raise AssertionError(output) from exc
        assert status == 200
        return health["runtime"]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _table_columns(db_path, table):
    with sqlite3.connect(db_path) as conn:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _columns(db_path):
    return _table_columns(db_path, "Notes")


def _column_default(db_path, column):
    with sqlite3.connect(db_path) as conn:
        for row in conn.execute("PRAGMA table_info(Notes)"):
            if row[1] == column:
                return row[4]
    return None


@pytest.fixture(scope="module")
def go_runtime(tmp_path_factory):
    """Build the Go exe once and fresh-init a Go-created DB (schema truth)."""
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; Go-sourced schema truth unavailable.")

    build_dir = tmp_path_factory.mktemp("schema_build")
    exe_path = build_go_shadow_exe(go_bin, build_dir)

    data_dir = tmp_path_factory.mktemp("schema_fresh") / "data"
    fresh_db = data_dir / "schema" / "fresh.db"
    runtime = _boot_and_inspect(exe_path, data_dir, "schema/fresh.db")
    assert runtime["schema_version"] == 17
    assert runtime["fresh_db_initialized"] is True
    # Collapse WAL so the file is self-contained for copy/inspect.
    with sqlite3.connect(fresh_db) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return {"exe_path": exe_path, "fresh_db": fresh_db}


def test_fresh_editor_layout_default_is_single(go_runtime):
    """Fresh Go-init DB must use the current editor_layout default."""
    default = _column_default(go_runtime["fresh_db"], "editor_layout")
    assert default == "'single'"
    assert default != "'full'"


def test_notes_type_column_absent(go_runtime):
    """Notes.type must be gone (migration v12 kill_notes_type)."""
    assert "type" not in _columns(go_runtime["fresh_db"]), (
        "Notes.type column still exists — migration v12 (kill_notes_type) regressed. "
        "This column was the root cause of 10.1 / 10.2."
    )


def test_notes_required_columns_present(go_runtime):
    """Core columns of the authoritative schema must all be present."""
    missing = REQUIRED_NOTES_COLUMNS - _columns(go_runtime["fresh_db"])
    assert not missing, f"Notes is missing columns: {missing}"


def test_categories_identity_columns_present(go_runtime):
    """System category identity must not depend on translated display names."""
    missing = REQUIRED_CATEGORY_COLUMNS - _table_columns(go_runtime["fresh_db"], "Categories")
    assert not missing, f"Categories is missing identity columns: {missing}"


def test_ai_columns_stripped(go_runtime):
    """AI columns removed in migration v14 must not exist."""
    present = STRIPPED_AI_COLUMNS & _columns(go_runtime["fresh_db"])
    assert not present, f"Stripped AI columns still present in Notes: {present}"


def test_existing_v15_db_editor_layout_normalized(go_runtime, tmp_path):
    """Migration v16 normalizes legacy editor_layout 'full'/NULL to 'single'.

    Seed a v15 DB by demoting a real Go-created DB (so every column is exactly
    the runtime's own schema, never a hand-rolled approximation), inject legacy
    editor_layout values, then let the Go existing-DB migration runner upgrade it.
    """
    data_dir = tmp_path / "data"
    (data_dir / "schema").mkdir(parents=True)
    legacy_db = data_dir / "schema" / "legacy.db"
    shutil.copy(go_runtime["fresh_db"], legacy_db)

    with sqlite3.connect(legacy_db) as conn:
        conn.executemany(
            "INSERT INTO Notes (title, content, editor_layout) VALUES (?, ?, ?)",
            [("legacy full", "body", "full"),
             ("legacy null", "body", None),
             ("valid dual", "body", "dual")],
        )
        conn.execute("UPDATE Schema_Meta SET value = '15' WHERE key = 'schema_version'")

    runtime = _boot_and_inspect(go_runtime["exe_path"], data_dir, "schema/legacy.db")
    assert runtime["schema_version"] == 17
    assert runtime["migrations_applied"] > 0

    with sqlite3.connect(legacy_db) as conn:
        rows = dict(
            conn.execute(
                "SELECT title, editor_layout FROM Notes "
                "WHERE title IN ('legacy full', 'legacy null', 'valid dual')"
            )
        )
        version = conn.execute(
            "SELECT value FROM Schema_Meta WHERE key = 'schema_version'"
        ).fetchone()[0]

    assert rows == {"legacy full": "single", "legacy null": "single", "valid dual": "dual"}
    assert version == "17"


def test_schema_gate_has_no_python_backend_imports():
    """Guard: this gate must stay valid after T053 deletes the Python source.

    If anyone reintroduces a Flask-backend import, this fails — keeping the
    schema truth genuinely Go-sourced and Python-independent.
    """
    forbidden = re.compile(
        r"^\s*(?:from|import)\s+(app|routes|migrations|services|config|db)\b",
        re.MULTILINE,
    )
    text = Path(__file__).read_text(encoding="utf-8")
    assert not forbidden.findall(text), "schema regression gate imports Python backend"
