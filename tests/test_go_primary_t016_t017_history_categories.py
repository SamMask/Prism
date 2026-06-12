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
HISTORY_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-notes-history-parity.json"
CATEGORIES_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-categories-parity.json"
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


def _start_go(db_path, data_dir, tmp_path, *, notes_write=False, category_write=False):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; contract/static checks still run.")

    port = _free_port()
    exe_path = build_go_shadow_exe(go_bin, tmp_path)
    args = [
        str(exe_path),
        "--db",
        db_path,
        "--addr",
        f"127.0.0.1:{port}",
        "--data-dir",
        str(data_dir),
    ]
    env = dict(os.environ)
    if notes_write:
        args.append("--enable-notes-write")
        env["PRISM_GO_ENABLE_NOTES_WRITE"] = "1"
    if category_write:
        args.append("--enable-category-write")
        env["PRISM_GO_ENABLE_CATEGORY_WRITE"] = "1"

    proc = subprocess.Popen(
        args,
        env=env,
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
    pytest.fail(f"Go T016/T017 candidate did not start:\n{output}")


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


def _seed_t016_t017_fixture(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        for name, icon, sort_order in (
            ("t017-source", "S", 940),
            ("t017-target", "T", 941),
            ("t017-empty", "E", 942),
        ):
            conn.execute(
                "INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES (?, ?, ?, 0)",
                (name, icon, sort_order),
            )
        ids = {
            "source": conn.execute("SELECT id FROM Categories WHERE name = 't017-source'").fetchone()[0],
            "target": conn.execute("SELECT id FROM Categories WHERE name = 't017-target'").fetchone()[0],
            "empty": conn.execute("SELECT id FROM Categories WHERE name = 't017-empty'").fetchone()[0],
            "default": conn.execute("SELECT id FROM Categories WHERE is_default = 1 LIMIT 1").fetchone()[0],
        }
        cursor = conn.execute(
            """
            INSERT INTO Notes (title, content, remarks, category_id)
            VALUES ('T016 History', 'current history content', 'history fixture', ?)
            """,
            (ids["source"],),
        )
        note_id = cursor.lastrowid
        history_rows = [
            ("old history content", "old diff", "2026-01-01 00:00:01"),
            ("restore target content", "restore diff", "2026-01-02 00:00:02"),
        ]
        history_ids = []
        for content, diff, created_at in history_rows:
            cursor = conn.execute(
                """
                INSERT INTO Note_History (note_id, content, diff_summary, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (note_id, content, diff, created_at),
            )
            history_ids.append(cursor.lastrowid)
        conn.commit()
        ids.update({"note": note_id, "history_old": history_ids[0], "history_restore": history_ids[1]})
        return ids
    finally:
        conn.close()


def _snapshot(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return {
            "categories": conn.execute(
                "SELECT id, name, icon, sort_order, COALESCE(is_default, 0) FROM Categories ORDER BY id"
            ).fetchall(),
            "notes": conn.execute("SELECT id, title, content, category_id FROM Notes ORDER BY id").fetchall(),
            "history": conn.execute(
                "SELECT id, note_id, content, diff_summary FROM Note_History ORDER BY id"
            ).fetchall(),
        }
    finally:
        conn.close()


def _scalar(db_path, query, args=()):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(query, args).fetchone()[0]
    finally:
        conn.close()


def test_t016_t017_contracts_record_local_candidate_boundaries():
    history_contract = _load_json(HISTORY_CONTRACT_PATH)
    categories_contract = _load_json(CATEGORIES_CONTRACT_PATH)
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")

    assert history_contract["task_id"] == "T016"
    assert history_contract["status"] == "completed_local_candidate"
    assert history_contract["covered_routes"] == [
        "GET /api/notes/<id>/history",
        "POST /api/notes/<id>/restore/<history_id>",
        "DELETE /api/notes/<id>/history",
    ]
    assert history_contract["runtime_boundary"]["production_db_write"] is False
    assert "getNoteHistory" in main_go
    assert "restoreNoteVersion" in main_go
    assert "deleteNoteHistory" in main_go

    assert categories_contract["task_id"] == "T017"
    assert categories_contract["status"] == "completed_local_candidate"
    assert categories_contract["covered_routes"] == [
        "POST /api/categories",
        "PUT /api/categories/<id>",
        "DELETE /api/categories/<id>",
    ]
    assert categories_contract["runtime_boundary"]["production_db_write"] is False
    assert "createCategory" in main_go
    assert "updateCategory" in main_go
    assert "deleteCategory" in main_go


def test_t016_t017_go_history_and_categories_match_python_response_and_db_state(temp_db, tmp_path):
    py_db = _copy_db(temp_db, tmp_path / "python_t016_t017.db")
    go_db = _copy_db(temp_db, tmp_path / "go_t016_t017.db")
    py_data = tmp_path / "python_data"
    go_data = tmp_path / "go_data"
    py_ids = _seed_t016_t017_fixture(py_db)
    go_ids = _seed_t016_t017_fixture(go_db)
    assert py_ids == go_ids

    client, ctx = _flask_client(py_db, py_data)
    proc, base = _start_go(go_db, go_data, tmp_path, notes_write=True, category_write=True)
    try:
        health_status, health_json = _request_json(base, "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["sqlite_query_only"] is False
        assert "local-notes-write" in health_json["runtime"]["api_surface"]
        assert "local-category-write" in health_json["runtime"]["api_surface"]

        path = f"/api/notes/{py_ids['note']}/history"
        py_response = client.get(path)
        go_status, go_json = _request_json(base, path)
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        py_response = client.get("/api/notes/999999/history")
        go_status, go_json = _request_json(base, "/api/notes/999999/history")
        assert go_status == py_response.status_code == 404
        assert go_json == py_response.get_json()

        before_py = _snapshot(py_db)
        before_go = _snapshot(go_db)
        missing_restore_path = f"/api/notes/{py_ids['note']}/restore/999999"
        py_response = client.post(missing_restore_path)
        go_status, go_json = _request_json(base, missing_restore_path, method="POST")
        assert go_status == py_response.status_code == 404
        assert go_json == py_response.get_json()
        assert _snapshot(py_db) == before_py
        assert _snapshot(go_db) == before_go

        restore_path = f"/api/notes/{py_ids['note']}/restore/{py_ids['history_restore']}"
        py_response = client.post(restore_path)
        go_status, go_json = _request_json(base, restore_path, method="POST")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        assert _scalar(py_db, "SELECT content FROM Notes WHERE id = ?", (py_ids["note"],)) == "restore target content"
        assert _scalar(go_db, "SELECT content FROM Notes WHERE id = ?", (py_ids["note"],)) == "restore target content"
        assert _scalar(
            py_db,
            "SELECT COUNT(*) FROM Note_History WHERE note_id = ? AND content = ? AND diff_summary = ?",
            (py_ids["note"], "current history content", "還原前自動備份"),
        ) == 1
        assert _scalar(
            go_db,
            "SELECT COUNT(*) FROM Note_History WHERE note_id = ? AND content = ? AND diff_summary = ?",
            (go_ids["note"], "current history content", "還原前自動備份"),
        ) == 1

        py_response = client.delete(path)
        go_status, go_json = _request_json(base, path, method="DELETE")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        assert _scalar(py_db, "SELECT COUNT(*) FROM Note_History WHERE note_id = ?", (py_ids["note"],)) == 0
        assert _scalar(go_db, "SELECT COUNT(*) FROM Note_History WHERE note_id = ?", (go_ids["note"],)) == 0

        py_response = client.delete("/api/notes/999999/history")
        go_status, go_json = _request_json(base, "/api/notes/999999/history", method="DELETE")
        assert go_status == py_response.status_code == 404
        assert go_json == py_response.get_json()

        create_payload = {"name": "T017 Created", "icon": "C", "sort_order": 950}
        py_response = client.post("/api/categories", json=create_payload)
        go_status, go_json = _request_json(base, "/api/categories", data=create_payload, method="POST")
        assert go_status == py_response.status_code == 201
        assert go_json == py_response.get_json()
        created_category_id = go_json["data"]["id"]

        py_response = client.post("/api/categories", json=create_payload)
        go_status, go_json = _request_json(base, "/api/categories", data=create_payload, method="POST")
        assert go_status == py_response.status_code == 409
        assert go_json == py_response.get_json()

        py_response = client.post("/api/categories", json={"icon": "M"})
        go_status, go_json = _request_json(base, "/api/categories", data={"icon": "M"}, method="POST")
        assert go_status == py_response.status_code == 400
        assert go_json == py_response.get_json()

        update_payload = {"name": "T017 Updated", "icon": "U", "sort_order": 951}
        py_response = client.put(f"/api/categories/{created_category_id}", json=update_payload)
        go_status, go_json = _request_json(
            base,
            f"/api/categories/{created_category_id}",
            data=update_payload,
            method="PUT",
        )
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        duplicate_update = {"name": "t017-target"}
        py_response = client.put(f"/api/categories/{created_category_id}", json=duplicate_update)
        go_status, go_json = _request_json(
            base,
            f"/api/categories/{created_category_id}",
            data=duplicate_update,
            method="PUT",
        )
        assert go_status == py_response.status_code == 409
        assert go_json == py_response.get_json()

        empty_update = {"name": "   "}
        py_response = client.put(f"/api/categories/{created_category_id}", json=empty_update)
        go_status, go_json = _request_json(
            base,
            f"/api/categories/{created_category_id}",
            data=empty_update,
            method="PUT",
        )
        assert go_status == py_response.status_code == 400
        assert go_json == py_response.get_json()

        py_response = client.delete(f"/api/categories/{py_ids['default']}", json={"target_category_id": py_ids["target"]})
        go_status, go_json = _request_json(
            base,
            f"/api/categories/{go_ids['default']}",
            data={"target_category_id": go_ids["target"]},
            method="DELETE",
        )
        assert go_status == py_response.status_code == 400
        assert go_json == py_response.get_json()

        py_response = client.delete(f"/api/categories/{py_ids['source']}", json={})
        go_status, go_json = _request_json(base, f"/api/categories/{go_ids['source']}", data={}, method="DELETE")
        assert go_status == py_response.status_code == 400
        assert go_json == py_response.get_json()

        migrate_payload = {"target_category_id": py_ids["target"]}
        py_response = client.delete(f"/api/categories/{py_ids['source']}", json=migrate_payload)
        go_status, go_json = _request_json(
            base,
            f"/api/categories/{go_ids['source']}",
            data={"target_category_id": go_ids["target"]},
            method="DELETE",
        )
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        assert _scalar(py_db, "SELECT category_id FROM Notes WHERE id = ?", (py_ids["note"],)) == py_ids["target"]
        assert _scalar(go_db, "SELECT category_id FROM Notes WHERE id = ?", (go_ids["note"],)) == go_ids["target"]

        py_response = client.delete(f"/api/categories/{py_ids['empty']}", json={})
        go_status, go_json = _request_json(base, f"/api/categories/{go_ids['empty']}", data={}, method="DELETE")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        py_response = client.delete("/api/categories/999999")
        go_status, go_json = _request_json(base, "/api/categories/999999", method="DELETE")
        assert go_status == py_response.status_code == 404
        assert go_json == py_response.get_json()
    finally:
        ctx.pop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert _snapshot(go_db) == _snapshot(py_db)


def test_t016_t017_default_runtime_keeps_history_and_category_writes_disabled(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t016_t017_disabled.db")
    go_data = tmp_path / "go_data"
    ids = _seed_t016_t017_fixture(go_db)

    before = _snapshot(go_db)
    proc, base = _start_go(go_db, go_data, tmp_path)
    try:
        health_status, health_json = _request_json(base, "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only"
        assert health_json["runtime"]["sqlite_query_only"] is True

        status, payload = _request_json(base, "/api/categories", data={"name": "Blocked"}, method="POST")
        assert status == 405
        assert payload["message"] == "Category write route is disabled"

        status, payload = _request_json(base, f"/api/categories/{ids['source']}", data={"name": "Blocked"}, method="PUT")
        assert status == 405
        assert payload["message"] == "Category write route is disabled"

        status, payload = _request_json(base, f"/api/categories/{ids['source']}", method="DELETE")
        assert status == 405
        assert payload["message"] == "Category write route is disabled"

        status, payload = _request_json(base, f"/api/notes/{ids['note']}/history")
        assert status == 405
        assert payload["message"] == "Notes write route is disabled"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert _snapshot(go_db) == before


def test_t016_t017_docs_mark_done_and_keep_runtime_boundaries():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    for task_id in ("T016", "T017"):
        row = next(line for line in todo.splitlines() if line.startswith(f"| {task_id} "))
        assert row.endswith("| Done |")

    t018_row = next(line for line in todo.splitlines() if line.startswith("| T018 "))
    t019_row = next(line for line in todo.splitlines() if line.startswith("| T019 "))
    t020_row = next(line for line in todo.splitlines() if line.startswith("| T020 "))
    assert t018_row.endswith("| Done |")
    assert t019_row.endswith("| Done |")
    assert t020_row.endswith("| Done |")
    assert "go-primary-notes-history-parity.json" in todo
    assert "go-primary-categories-parity.json" in todo
    assert "T016/T017 Go notes history and categories parity gate is complete" in architecture
    assert "Go T016/T017" in schema
    assert "Notes History And Categories" in readme
    assert "T016/T017" in go_report
    assert "does not promote live/default notes or taxonomy write ownership" in architecture
