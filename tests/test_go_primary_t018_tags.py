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
TAGS_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-tags-parity.json"
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


def _start_go(db_path, data_dir, tmp_path, *, tag_write=False, notes_write=False):
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
    if tag_write:
        args.append("--enable-tag-write")
        env["PRISM_GO_ENABLE_TAG_WRITE"] = "1"
    if notes_write:
        args.append("--enable-notes-write")
        env["PRISM_GO_ENABLE_NOTES_WRITE"] = "1"

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
    pytest.fail(f"Go T018 candidate did not start:\n{output}")


def _flask_client(db_path, data_dir):
    from app import create_app

    Path(data_dir).mkdir(parents=True, exist_ok=True)
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


def _insert_tag(conn, name):
    cursor = conn.execute("INSERT INTO Tags (name) VALUES (?)", (name,))
    return cursor.lastrowid


def _insert_note(conn, title, category_id):
    cursor = conn.execute(
        """
        INSERT INTO Notes (title, content, remarks, category_id)
        VALUES (?, ?, 't018 fixture', ?)
        """,
        (title, f"{title} content", category_id),
    )
    return cursor.lastrowid


def _seed_t018_fixture(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        default_category = conn.execute(
            "SELECT id FROM Categories WHERE is_default = 1 LIMIT 1"
        ).fetchone()[0]
        ids = {
            "alpha": _insert_tag(conn, "t018-alpha"),
            "beta": _insert_tag(conn, "t018-beta"),
            "delete": _insert_tag(conn, "t018-delete"),
            "source1": _insert_tag(conn, "t018-source-1"),
            "source2": _insert_tag(conn, "t018-source-2"),
            "target": _insert_tag(conn, "t018-target"),
            "case_existing": _insert_tag(conn, "t018-case-existing"),
        }
        ids.update(
            {
                "delete_note": _insert_note(conn, "T018 Delete", default_category),
                "merge_note_1": _insert_note(conn, "T018 Merge One", default_category),
                "merge_note_2": _insert_note(conn, "T018 Merge Two", default_category),
                "already_target_note": _insert_note(conn, "T018 Merge Existing Target", default_category),
                "case_note": _insert_note(conn, "T018 Case Note", default_category),
            }
        )
        for note_id, tag_id in (
            (ids["delete_note"], ids["delete"]),
            (ids["merge_note_1"], ids["source1"]),
            (ids["merge_note_2"], ids["source2"]),
            (ids["already_target_note"], ids["source1"]),
            (ids["already_target_note"], ids["target"]),
        ):
            conn.execute("INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))
        conn.commit()
        return ids
    finally:
        conn.close()


def _snapshot(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return {
            "tags": conn.execute("SELECT id, name FROM Tags ORDER BY id").fetchall(),
            "note_tags": conn.execute("SELECT note_id, tag_id FROM Note_Tags ORDER BY note_id, tag_id").fetchall(),
            "notes": conn.execute("SELECT id, title, content FROM Notes ORDER BY id").fetchall(),
        }
    finally:
        conn.close()


def _scalar(db_path, query, args=()):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(query, args).fetchone()[0]
    finally:
        conn.close()


def test_t018_contract_records_local_candidate_boundaries():
    contract = _load_json(TAGS_CONTRACT_PATH)
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")

    assert contract["task_id"] == "T018"
    assert contract["status"] == "completed_local_candidate"
    assert contract["covered_routes"] == [
        "PUT /api/tags/<id>",
        "DELETE /api/tags/<id>",
        "POST /api/tags/merge",
    ]
    assert contract["create_route_boundary"]["POST /api/tags"] == "not a current Python API route"
    assert contract["runtime_boundary"]["production_db_write"] is False
    assert contract["runtime_boundary"]["go_default_write_owner"] is False
    assert "renameTag" in main_go
    assert "deleteTag" in main_go
    assert "mergeTags" in main_go
    assert "http.MethodDelete" in main_go
    assert "http.MethodPost" in main_go
    assert "COLLATE NOCASE" in main_go


def test_t018_go_tags_write_merge_and_nocase_match_python_response_and_db_state(temp_db, tmp_path):
    py_db = _copy_db(temp_db, tmp_path / "python_t018.db")
    go_db = _copy_db(temp_db, tmp_path / "go_t018.db")
    py_data = tmp_path / "python_data"
    go_data = tmp_path / "go_data"
    py_ids = _seed_t018_fixture(py_db)
    go_ids = _seed_t018_fixture(go_db)
    assert py_ids == go_ids

    client, ctx = _flask_client(py_db, py_data)
    proc, base = _start_go(go_db, go_data, tmp_path, tag_write=True, notes_write=True)
    try:
        health_status, health_json = _request_json(base, "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["sqlite_query_only"] is False
        assert health_json["runtime"]["api_surface"] == "get-read-only+local-tag-write+local-notes-write"

        rename_payload = {"name": "  t018-renamed  "}
        py_response = client.put(f"/api/tags/{py_ids['alpha']}", json=rename_payload)
        go_status, go_json = _request_json(base, f"/api/tags/{go_ids['alpha']}", data=rename_payload, method="PUT")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        assert _snapshot(go_db) == _snapshot(py_db)

        before_py = _snapshot(py_db)
        before_go = _snapshot(go_db)
        duplicate_payload = {"name": "T018-RENAMED"}
        py_response = client.put(f"/api/tags/{py_ids['beta']}", json=duplicate_payload)
        go_status, go_json = _request_json(base, f"/api/tags/{go_ids['beta']}", data=duplicate_payload, method="PUT")
        assert go_status == py_response.status_code == 409
        assert go_json == py_response.get_json()
        assert _snapshot(py_db) == before_py
        assert _snapshot(go_db) == before_go

        py_response = client.delete(f"/api/tags/{py_ids['delete']}")
        go_status, go_json = _request_json(base, f"/api/tags/{go_ids['delete']}", method="DELETE")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        assert _scalar(py_db, "SELECT COUNT(*) FROM Tags WHERE id = ?", (py_ids["delete"],)) == 0
        assert _scalar(go_db, "SELECT COUNT(*) FROM Tags WHERE id = ?", (go_ids["delete"],)) == 0
        assert _scalar(py_db, "SELECT COUNT(*) FROM Note_Tags WHERE tag_id = ?", (py_ids["delete"],)) == 0
        assert _scalar(go_db, "SELECT COUNT(*) FROM Note_Tags WHERE tag_id = ?", (go_ids["delete"],)) == 0
        assert _snapshot(go_db) == _snapshot(py_db)

        py_response = client.delete("/api/tags/999999")
        go_status, go_json = _request_json(base, "/api/tags/999999", method="DELETE")
        assert go_status == py_response.status_code == 404
        assert go_json == py_response.get_json()

        before_py = _snapshot(py_db)
        before_go = _snapshot(go_db)
        missing_target = {"source_tag_ids": [py_ids["source1"]], "target_tag_id": 999999}
        py_response = client.post("/api/tags/merge", json=missing_target)
        go_status, go_json = _request_json(
            base,
            "/api/tags/merge",
            data={"source_tag_ids": [go_ids["source1"]], "target_tag_id": 999999},
            method="POST",
        )
        assert go_status == py_response.status_code == 404
        assert go_json == py_response.get_json()
        assert _snapshot(py_db) == before_py
        assert _snapshot(go_db) == before_go

        invalid_cases = [
            ({}, {}),
            ({"source_tag_ids": [], "target_tag_id": py_ids["target"]}, {"source_tag_ids": [], "target_tag_id": go_ids["target"]}),
            (
                {"source_tag_ids": [py_ids["target"]], "target_tag_id": py_ids["target"]},
                {"source_tag_ids": [go_ids["target"]], "target_tag_id": go_ids["target"]},
            ),
        ]
        for py_payload, go_payload in invalid_cases:
            py_response = client.post("/api/tags/merge", json=py_payload)
            go_status, go_json = _request_json(base, "/api/tags/merge", data=go_payload, method="POST")
            assert go_status == py_response.status_code == 400
            assert go_json == py_response.get_json()

        merge_payload_py = {
            "source_tag_ids": [py_ids["source1"], 999999, py_ids["source2"]],
            "target_tag_id": py_ids["target"],
        }
        merge_payload_go = {
            "source_tag_ids": [go_ids["source1"], 999999, go_ids["source2"]],
            "target_tag_id": go_ids["target"],
        }
        py_response = client.post("/api/tags/merge", json=merge_payload_py)
        go_status, go_json = _request_json(base, "/api/tags/merge", data=merge_payload_go, method="POST")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json() == {"status": "success", "data": {"merged_count": 2}}
        assert _scalar(py_db, "SELECT COUNT(*) FROM Tags WHERE id IN (?, ?)", (py_ids["source1"], py_ids["source2"])) == 0
        assert _scalar(go_db, "SELECT COUNT(*) FROM Tags WHERE id IN (?, ?)", (go_ids["source1"], go_ids["source2"])) == 0
        assert _scalar(py_db, "SELECT COUNT(*) FROM Note_Tags WHERE tag_id = ?", (py_ids["target"],)) == 3
        assert _scalar(go_db, "SELECT COUNT(*) FROM Note_Tags WHERE tag_id = ?", (go_ids["target"],)) == 3
        assert _snapshot(go_db) == _snapshot(py_db)

        batch_payload_py = {
            "note_ids": [py_ids["case_note"]],
            "tags": ["T018-CASE-EXISTING"],
            "mode": "append",
        }
        batch_payload_go = {
            "note_ids": [go_ids["case_note"]],
            "tags": ["T018-CASE-EXISTING"],
            "mode": "append",
        }
        py_response = client.post("/api/notes/batch/tags", json=batch_payload_py)
        go_status, go_json = _request_json(base, "/api/notes/batch/tags", data=batch_payload_go, method="POST")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        assert _scalar(py_db, "SELECT COUNT(*) FROM Tags WHERE name = ? COLLATE NOCASE", ("t018-case-existing",)) == 1
        assert _scalar(go_db, "SELECT COUNT(*) FROM Tags WHERE name = ? COLLATE NOCASE", ("t018-case-existing",)) == 1
        assert _scalar(py_db, "SELECT COUNT(*) FROM Note_Tags WHERE note_id = ? AND tag_id = ?", (py_ids["case_note"], py_ids["case_existing"])) == 1
        assert _scalar(go_db, "SELECT COUNT(*) FROM Note_Tags WHERE note_id = ? AND tag_id = ?", (go_ids["case_note"], go_ids["case_existing"])) == 1
        assert _snapshot(go_db) == _snapshot(py_db)

        before_py = _snapshot(py_db)
        before_go = _snapshot(go_db)
        py_response = client.post("/api/tags", json={"name": "t018-no-route"})
        go_status, _ = _request_json(base, "/api/tags", data={"name": "t018-no-route"}, method="POST")
        assert go_status == py_response.status_code == 405
        assert _snapshot(py_db) == before_py
        assert _snapshot(go_db) == before_go
    finally:
        ctx.pop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_t018_default_runtime_keeps_tag_writes_disabled(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t018_disabled.db")
    go_data = tmp_path / "go_data"
    ids = _seed_t018_fixture(go_db)
    before = _snapshot(go_db)

    proc, base = _start_go(go_db, go_data, tmp_path)
    try:
        health_status, health_json = _request_json(base, "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only"
        assert health_json["runtime"]["sqlite_query_only"] is True

        status, payload = _request_json(base, f"/api/tags/{ids['alpha']}", data={"name": "blocked"}, method="PUT")
        assert status == 405
        assert payload["message"] == "Tag write route is disabled"

        status, payload = _request_json(base, f"/api/tags/{ids['delete']}", method="DELETE")
        assert status == 405
        assert payload["message"] == "Tag write route is disabled"

        status, payload = _request_json(
            base,
            "/api/tags/merge",
            data={"source_tag_ids": [ids["source1"]], "target_tag_id": ids["target"]},
            method="POST",
        )
        assert status == 405
        assert payload["message"] == "Tag write route is disabled"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert _snapshot(go_db) == before


def test_t018_docs_mark_done_and_keep_runtime_boundaries():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    t018_row = next(line for line in todo.splitlines() if line.startswith("| T018 "))
    t019_row = next(line for line in todo.splitlines() if line.startswith("| T019 "))
    t020_row = next(line for line in todo.splitlines() if line.startswith("| T020 "))
    assert t018_row.endswith("| Done |")
    assert t019_row.endswith("| Done |")
    assert t020_row.endswith("| Todo |")
    assert "go-primary-tags-parity.json" in todo
    assert "T018 Go tags parity gate is complete" in architecture
    assert "Go T018" in schema
    assert "Tags Write And Merge" in readme
    assert "T018" in go_report
    assert "does not promote live/default taxonomy write ownership" in architecture
