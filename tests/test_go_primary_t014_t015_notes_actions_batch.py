import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tests.go_primary_parity_harness import build_go_shadow_exe


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"
ACTIONS_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-notes-actions-parity.json"
BATCH_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-notes-batch-actions-parity.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
GO_README_PATH = GO_SHADOW_DIR / "README.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
GO_MAIN_PATH = GO_SHADOW_DIR / "main.go"


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_db(src, dst):
    shutil.copyfile(src, dst)
    return str(dst)


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _request_json(base, path, *, data=None, method="GET"):
    body = None if data is None else json.dumps(data).encode("utf-8")
    last_error = None
    for attempt in range(5):
        request = urllib.request.Request(base.rstrip("/") + path, data=body, method=method)
        if body is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                payload = response.read().decode("utf-8")
                return response.status, json.loads(payload) if payload else None
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8")
            try:
                parsed = json.loads(payload) if payload else None
            except json.JSONDecodeError:
                parsed = payload
            return exc.code, parsed
        except (ConnectionError, TimeoutError, urllib.error.URLError):
            last_error = sys.exc_info()[1]
            if attempt < 4:
                time.sleep(0.1 * (attempt + 1))
                continue
            raise last_error
    raise AssertionError("unreachable request retry state")


def _start_go(db_path, data_dir, tmp_path):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; contract/static checks still run.")

    port = _free_port()
    exe_path = build_go_shadow_exe(go_bin, tmp_path)
    proc = subprocess.Popen(
        [
            str(exe_path),
            "--db",
            db_path,
            "--addr",
            f"127.0.0.1:{port}",
            "--data-dir",
            str(data_dir),
            "--enable-notes-write",
        ],
        env={**os.environ, "PRISM_GO_ENABLE_NOTES_WRITE": "1"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            _request_json(base, "/api/test")
            return proc, base
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.25)

    output = proc.stdout.read() if proc.stdout else ""
    proc.terminate()
    pytest.fail(f"Go notes actions/batch candidate did not start:\n{output}")


def _flask_client(db_path, data_dir):
    from app import create_app

    app = create_app("testing")
    app.config.update(
        {
            "TESTING": True,
            "DATABASE": db_path,
            "WTF_CSRF_ENABLED": False,
            "PROPAGATE_EXCEPTIONS": True,
        }
    )
    app.root_path = str(data_dir)
    ctx = app.app_context()
    ctx.push()
    return app.test_client(), ctx


def _seed_t014_t015_fixture(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES ('t014-alpha', 'A', 930, 0)")
        conn.execute("INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES ('t015-beta', 'B', 931, 0)")
        alpha = conn.execute("SELECT id FROM Categories WHERE name = 't014-alpha'").fetchone()[0]
        beta = conn.execute("SELECT id FROM Categories WHERE name = 't015-beta'").fetchone()[0]
        conn.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('t014-seed-tag')")
        seed_tag = conn.execute("SELECT id FROM Tags WHERE name = 't014-seed-tag'").fetchone()[0]

        def note(title, content, sort_order):
            cursor = conn.execute(
                """
                INSERT INTO Notes (title, content, remarks, category_id, sort_order, prompt_params)
                VALUES (?, ?, 'fixture remarks', ?, ?, '{"kind": "fixture"}')
                """,
                (title, content, alpha, sort_order),
            )
            return cursor.lastrowid

        action = note("T014 Action", "action content", 10)
        reorder_a = note("T014 Reorder A", "reorder a", 20)
        reorder_b = note("T014 Reorder B", "reorder b", 30)
        batch_a = note("T015 Batch A", "batch a", 40)
        batch_b = note("T015 Batch B", "batch b", 50)
        for note_id in (action, batch_a):
            conn.execute("INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", (note_id, seed_tag))
            conn.execute("INSERT INTO Source_Urls (note_id, url) VALUES (?, ?)", (note_id, f"https://t014.example/{note_id}"))
        conn.commit()
        return {
            "alpha": alpha,
            "beta": beta,
            "action": action,
            "reorder_a": reorder_a,
            "reorder_b": reorder_b,
            "batch_a": batch_a,
            "batch_b": batch_b,
        }
    finally:
        conn.close()


def _snapshot(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return {
            "notes": conn.execute(
                """
                SELECT id, title, content, remarks, cover_image, cover_position, editor_layout,
                       category_id, prompt_params, parent_id, COALESCE(is_pinned, 0),
                       COALESCE(is_archived, 0), COALESCE(sort_order, 0)
                FROM Notes ORDER BY id
                """
            ).fetchall(),
            "tags": conn.execute("SELECT id, name FROM Tags ORDER BY id").fetchall(),
            "note_tags": conn.execute("SELECT note_id, tag_id FROM Note_Tags ORDER BY note_id, tag_id").fetchall(),
            "urls": conn.execute("SELECT note_id, url FROM Source_Urls ORDER BY note_id, id").fetchall(),
        }
    finally:
        conn.close()


def _scalar(db_path, query, args=()):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(query, args).fetchone()[0]
    finally:
        conn.close()


def test_t014_t015_contracts_record_local_candidate_boundaries():
    actions_contract = _load_json(ACTIONS_CONTRACT_PATH)
    batch_contract = _load_json(BATCH_CONTRACT_PATH)
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")

    assert actions_contract["task_id"] == "T014"
    assert actions_contract["status"] == "completed_local_candidate"
    assert actions_contract["covered_routes"] == [
        "POST /api/notes/<id>/pin",
        "POST /api/notes/<id>/archive",
        "POST /api/notes/<id>/duplicate",
        "PUT /api/notes/reorder",
    ]
    assert actions_contract["runtime_boundary"]["production_db_write"] is False
    assert "toggleNoteBool" in main_go
    assert "duplicateNote" in main_go
    assert "reorderNotes" in main_go

    assert batch_contract["task_id"] == "T015"
    assert batch_contract["status"] == "completed_local_candidate"
    assert batch_contract["covered_routes"] == ["POST /api/notes/batch/type", "POST /api/notes/batch/tags"]
    assert batch_contract["current_python_batch_archive_route"] is False
    assert "batchUpdateType" in main_go
    assert "batchUpdateTags" in main_go
    assert "archive" not in batch_contract["covered_routes"]


def test_t014_t015_go_actions_and_batch_match_python_response_and_db_state(temp_db, tmp_path):
    py_db = _copy_db(temp_db, tmp_path / "python_t014_t015_notes.db")
    go_db = _copy_db(temp_db, tmp_path / "go_t014_t015_notes.db")
    py_data = tmp_path / "python_data"
    go_data = tmp_path / "go_data"
    py_ids = _seed_t014_t015_fixture(py_db)
    go_ids = _seed_t014_t015_fixture(go_db)
    assert py_ids == go_ids

    client, ctx = _flask_client(py_db, py_data)
    proc, base = _start_go(go_db, go_data, tmp_path)
    try:
        health_status, health_json = _request_json(base, "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only+local-notes-write"
        assert health_json["runtime"]["sqlite_query_only"] is False

        for path, payload in [
            (f"/api/notes/{py_ids['action']}/pin", {"pinned": True}),
            (f"/api/notes/{py_ids['action']}/pin", None),
            (f"/api/notes/{py_ids['action']}/archive", {"archived": True}),
            (f"/api/notes/{py_ids['action']}/archive", {"archived": False}),
        ]:
            py_response = client.post(path, json=payload) if payload is not None else client.post(path)
            go_status, go_json = _request_json(base, path, data=payload, method="POST")
            assert go_status == py_response.status_code == 200
            assert go_json == py_response.get_json()

        py_missing = client.post("/api/notes/999999/pin", json={"pinned": True})
        go_missing_status, go_missing_json = _request_json(base, "/api/notes/999999/pin", data={"pinned": True}, method="POST")
        assert go_missing_status == py_missing.status_code == 404
        assert go_missing_json == py_missing.get_json()

        duplicate_payload = {"as_variant": True, "title_suffix": " (T014 Variant)"}
        py_response = client.post(f"/api/notes/{py_ids['action']}/duplicate", json=duplicate_payload)
        go_status, go_json = _request_json(
            base,
            f"/api/notes/{go_ids['action']}/duplicate",
            data=duplicate_payload,
            method="POST",
        )
        assert go_status == py_response.status_code == 201
        assert go_json == py_response.get_json()
        variant_id = go_json["data"]["note_id"]

        reorder_payload = {"note_ids": [variant_id, py_ids["reorder_b"], py_ids["reorder_a"], py_ids["action"]]}
        py_response = client.put("/api/notes/reorder", json=reorder_payload)
        go_status, go_json = _request_json(base, "/api/notes/reorder", data=reorder_payload, method="PUT")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        for index, note_id in enumerate(reorder_payload["note_ids"]):
            assert _scalar(py_db, "SELECT sort_order FROM Notes WHERE id = ?", (note_id,)) == index
            assert _scalar(go_db, "SELECT sort_order FROM Notes WHERE id = ?", (note_id,)) == index

        for bad_payload in ({"note_ids": []}, {"note_ids": [py_ids["action"], "bad"]}):
            py_response = client.put("/api/notes/reorder", json=bad_payload)
            go_status, go_json = _request_json(base, "/api/notes/reorder", data=bad_payload, method="PUT")
            assert go_status == py_response.status_code == 400
            assert go_json == py_response.get_json()

        type_payload = {"note_ids": [py_ids["batch_a"], py_ids["batch_b"], 999999], "category_id": py_ids["beta"]}
        py_response = client.post("/api/notes/batch/type", json=type_payload)
        go_status, go_json = _request_json(base, "/api/notes/batch/type", data=type_payload, method="POST")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        assert go_json["data"]["updated_count"] == 2

        before_py = _snapshot(py_db)
        before_go = _snapshot(go_db)
        invalid_type = {"note_ids": [py_ids["batch_a"]], "category_id": 999999}
        py_response = client.post("/api/notes/batch/type", json=invalid_type)
        go_status, go_json = _request_json(base, "/api/notes/batch/type", data=invalid_type, method="POST")
        assert go_status == py_response.status_code == 400
        assert go_json == py_response.get_json()
        assert _snapshot(py_db) == before_py
        assert _snapshot(go_db) == before_go

        tags_append = {"note_ids": [py_ids["batch_a"], py_ids["batch_b"], 999999], "tags": ["t015-added"], "mode": "append"}
        py_response = client.post("/api/notes/batch/tags", json=tags_append)
        go_status, go_json = _request_json(base, "/api/notes/batch/tags", data=tags_append, method="POST")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        assert go_json["data"] == {"affected_notes": 2, "tags_added": 2, "mode": "append"}

        tags_replace = {"note_ids": [py_ids["batch_a"]], "tags": ["t015-replaced"], "mode": "replace"}
        py_response = client.post("/api/notes/batch/tags", json=tags_replace)
        go_status, go_json = _request_json(base, "/api/notes/batch/tags", data=tags_replace, method="POST")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        for bad_payload in (
            {"note_ids": [], "tags": ["x"]},
            {"note_ids": [py_ids["batch_a"]], "tags": ["x"], "mode": "invalid"},
            {"note_ids": [py_ids["batch_a"], "bad"], "tags": ["x"]},
        ):
            py_response = client.post("/api/notes/batch/tags", json=bad_payload)
            go_status, go_json = _request_json(base, "/api/notes/batch/tags", data=bad_payload, method="POST")
            assert go_status == py_response.status_code == 400
            assert go_json == py_response.get_json()

        py_archive_status = client.post("/api/notes/batch/archive", json={"note_ids": [py_ids["batch_a"]]}).status_code
        go_archive_status, go_archive_json = _request_json(
            base,
            "/api/notes/batch/archive",
            data={"note_ids": [py_ids["batch_a"]]},
            method="POST",
        )
        assert py_archive_status == 404
        assert go_archive_status == 404
        assert isinstance(go_archive_json, str)
    finally:
        ctx.pop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert _snapshot(go_db) == _snapshot(py_db)


def test_t014_t015_docs_mark_done_and_keep_runtime_boundaries():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    for task_id in ("T014", "T015"):
        row = next(line for line in todo.splitlines() if line.startswith(f"| {task_id} "))
        assert row.endswith("| Done |")

    t016_row = next(line for line in todo.splitlines() if line.startswith("| T016 "))
    t017_row = next(line for line in todo.splitlines() if line.startswith("| T017 "))
    t018_row = next(line for line in todo.splitlines() if line.startswith("| T018 "))
    t019_row = next(line for line in todo.splitlines() if line.startswith("| T019 "))
    t020_row = next(line for line in todo.splitlines() if line.startswith("| T020 "))
    assert t016_row.endswith("| Done |")
    assert t017_row.endswith("| Done |")
    assert t018_row.endswith("| Done |")
    assert t019_row.endswith("| Done |")
    assert t020_row.endswith("| Todo |")
    assert "go-primary-notes-actions-parity.json" in todo
    assert "go-primary-notes-batch-actions-parity.json" in todo
    assert "T014/T015 Go notes actions and batch type/tags parity gate is complete" in architecture
    assert "Go T014/T015" in schema
    assert "Notes Actions And Batch Type/Tags" in readme
    assert "T014/T015" in go_report
    assert "does not promote live/default notes write ownership" in architecture
