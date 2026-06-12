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
DELETE_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-notes-delete-parity.json"
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
    request = urllib.request.Request(base.rstrip("/") + path, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        return exc.code, json.loads(payload) if payload else None


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
    pytest.fail(f"Go notes delete candidate did not start:\n{output}")


def _flask_client(db_path, data_dir):
    from app import create_app

    uploads_dir = Path(data_dir) / "static" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app = create_app("testing")
    app.config.update(
        {
            "TESTING": True,
            "DATABASE": db_path,
            "UPLOAD_FOLDER": str(uploads_dir),
            "WTF_CSRF_ENABLED": False,
            "PROPAGATE_EXCEPTIONS": True,
        }
    )
    app.root_path = str(data_dir)
    ctx = app.app_context()
    ctx.push()
    return app.test_client(), ctx


def _seed_t013_fixture(db_path, data_dir):
    uploads = Path(data_dir) / "static" / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    for name in (
        "single.jpg",
        "single_thumb.webp",
        "cover.jpg",
        "cover_thumb.webp",
        "shared.jpg",
        "shared_thumb.webp",
        "batch-a.jpg",
        "batch-a_thumb.webp",
        "batch-thumb_thumb.webp",
        "batch-thumb.jpg",
    ):
        (uploads / name).write_bytes(name.encode("utf-8"))

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        category_id = conn.execute("SELECT id FROM Categories WHERE is_default = 1 LIMIT 1").fetchone()[0]
        conn.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('t013-delete-tag')")
        tag_id = conn.execute("SELECT id FROM Tags WHERE name = 't013-delete-tag'").fetchone()[0]

        def note(title, content, cover_image=None):
            cursor = conn.execute(
                """
                INSERT INTO Notes (title, content, cover_image, category_id)
                VALUES (?, ?, ?, ?)
                """,
                (title, content, cover_image, category_id),
            )
            return cursor.lastrowid

        single = note(
            "T013 Single",
            "singleftstoken ![](/static/uploads/single.jpg)",
            "/static/uploads/cover.jpg",
        )
        shared_delete = note("T013 Shared Delete", "sharedftstoken ![](/static/uploads/shared.jpg)")
        shared_keep = note("T013 Shared Keep", "sharedftstoken ![](/static/uploads/shared.jpg)")
        batch_a = note("T013 Batch A", "batchaftstoken ![](/static/uploads/batch-a.jpg)")
        batch_b = note("T013 Batch B", "batchbftstoken", "/static/uploads/batch-thumb_thumb.webp")

        for note_id in (single, batch_a):
            conn.execute("INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))
            conn.execute("INSERT INTO Source_Urls (note_id, url) VALUES (?, ?)", (note_id, f"https://t013.example/{note_id}"))
            conn.execute(
                "INSERT INTO Note_History (note_id, content, diff_summary) VALUES (?, 'old content', 'history row')",
                (note_id,),
            )
            conn.execute(
                """
                INSERT INTO Note_Attachments (note_id, file_path, file_type, title)
                VALUES (?, 'docs/attachments/t013.md', 'md', 'delete attachment')
                """,
                (note_id,),
            )
        conn.commit()
        return {
            "single": single,
            "shared_delete": shared_delete,
            "shared_keep": shared_keep,
            "batch_a": batch_a,
            "batch_b": batch_b,
        }
    finally:
        conn.close()


def _scalar(db_path, query, args=()):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(query, args).fetchone()[0]
    finally:
        conn.close()


def _file_exists(data_dir, name):
    return (Path(data_dir) / "static" / "uploads" / name).exists()


def _assert_deleted_note_state(db_path, note_id):
    assert _scalar(db_path, "SELECT COUNT(*) FROM Notes WHERE id = ?", (note_id,)) == 0
    assert _scalar(db_path, "SELECT COUNT(*) FROM Note_Tags WHERE note_id = ?", (note_id,)) == 0
    assert _scalar(db_path, "SELECT COUNT(*) FROM Source_Urls WHERE note_id = ?", (note_id,)) == 0
    assert _scalar(db_path, "SELECT COUNT(*) FROM Note_History WHERE note_id = ?", (note_id,)) == 0
    assert _scalar(db_path, "SELECT COUNT(*) FROM Note_Attachments WHERE note_id = ?", (note_id,)) == 0


def test_t013_contract_records_delete_scope_and_media_cleanup_decision():
    contract = _load_json(DELETE_CONTRACT_PATH)
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")

    assert contract["task_id"] == "T013"
    assert contract["status"] == "completed_local_candidate"
    assert contract["production_runtime_owner"] == "python"
    assert contract["enable_flag"] == "--enable-notes-write"
    assert contract["covered_routes"] == ["DELETE /api/notes/<id>", "POST /api/notes/batch/delete"]
    assert contract["cleanup_decision"] == {
        "extract_static_uploads_from": ["Notes.content", "Notes.cover_image"],
        "delete_only_when_no_other_note_references_path": True,
        "delete_original_companion": "_thumb.webp",
        "delete_thumb_companion_candidates": [".jpg", ".png", ".gif", ".webp"],
        "path_scope": "PRISM_GO_DATA_DIR/static/uploads only",
    }
    assert contract["runtime_boundary"]["production_file_write"] is False
    assert "cleanupNoteImages" in main_go
    assert "staticUploadReferencePattern" in main_go
    assert "cleanupUploadFilenames" in main_go
    assert "_thumb.webp" in main_go
    assert "Note_Attachments" in main_go


def test_t013_go_notes_delete_and_batch_delete_match_python_db_and_file_state(temp_db, tmp_path):
    py_db = _copy_db(temp_db, tmp_path / "python_t013_notes_delete.db")
    go_db = _copy_db(temp_db, tmp_path / "go_t013_notes_delete.db")
    py_data = tmp_path / "python_data"
    go_data = tmp_path / "go_data"
    py_ids = _seed_t013_fixture(py_db, py_data)
    go_ids = _seed_t013_fixture(go_db, go_data)
    assert py_ids == go_ids

    client, ctx = _flask_client(py_db, py_data)
    proc, base = _start_go(go_db, go_data, tmp_path)
    try:
        health_status, health_json = _request_json(base, "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only+local-notes-write"
        assert health_json["runtime"]["sqlite_query_only"] is False

        py_response = client.delete(f"/api/notes/{py_ids['single']}")
        go_status, go_json = _request_json(base, f"/api/notes/{go_ids['single']}", method="DELETE")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        for db_path in (py_db, go_db):
            _assert_deleted_note_state(db_path, py_ids["single"])
            assert _scalar(db_path, "SELECT COUNT(*) FROM Notes_FTS WHERE Notes_FTS MATCH ?", ("singleftstoken",)) == 0
        for data_dir in (py_data, go_data):
            for name in ("single.jpg", "single_thumb.webp", "cover.jpg", "cover_thumb.webp"):
                assert not _file_exists(data_dir, name), name

        py_missing = client.delete("/api/notes/999999")
        go_missing_status, go_missing_json = _request_json(base, "/api/notes/999999", method="DELETE")
        assert go_missing_status == py_missing.status_code == 404
        assert go_missing_json == py_missing.get_json()

        py_response = client.delete(f"/api/notes/{py_ids['shared_delete']}")
        go_status, go_json = _request_json(base, f"/api/notes/{go_ids['shared_delete']}", method="DELETE")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        for db_path in (py_db, go_db):
            assert _scalar(db_path, "SELECT COUNT(*) FROM Notes WHERE id = ?", (py_ids["shared_keep"],)) == 1
        for data_dir in (py_data, go_data):
            assert _file_exists(data_dir, "shared.jpg")
            assert _file_exists(data_dir, "shared_thumb.webp")

        batch_payload = {"note_ids": [py_ids["batch_a"], py_ids["batch_b"], 999999]}
        py_response = client.post("/api/notes/batch/delete", json=batch_payload)
        go_status, go_json = _request_json(base, "/api/notes/batch/delete", data=batch_payload, method="POST")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        assert go_json["data"]["deleted_count"] == 2
        for db_path in (py_db, go_db):
            _assert_deleted_note_state(db_path, py_ids["batch_a"])
            _assert_deleted_note_state(db_path, py_ids["batch_b"])
            assert _scalar(db_path, "SELECT COUNT(*) FROM Notes_FTS WHERE Notes_FTS MATCH ?", ("batchaftstoken",)) == 0
            assert _scalar(db_path, "SELECT COUNT(*) FROM Notes_FTS WHERE Notes_FTS MATCH ?", ("batchbftstoken",)) == 0
        for data_dir in (py_data, go_data):
            for name in ("batch-a.jpg", "batch-a_thumb.webp", "batch-thumb_thumb.webp", "batch-thumb.jpg"):
                assert not _file_exists(data_dir, name), name

        py_empty = client.post("/api/notes/batch/delete", json={"note_ids": []})
        go_empty_status, go_empty_json = _request_json(base, "/api/notes/batch/delete", data={"note_ids": []}, method="POST")
        assert go_empty_status == py_empty.status_code == 400
        assert go_empty_json == py_empty.get_json()
    finally:
        ctx.pop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_t013_docs_mark_done_and_keep_runtime_boundaries():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    t013_row = next(line for line in todo.splitlines() if line.startswith("| T013 "))
    t014_row = next(line for line in todo.splitlines() if line.startswith("| T014 "))
    t015_row = next(line for line in todo.splitlines() if line.startswith("| T015 "))
    t016_row = next(line for line in todo.splitlines() if line.startswith("| T016 "))
    t017_row = next(line for line in todo.splitlines() if line.startswith("| T017 "))
    t018_row = next(line for line in todo.splitlines() if line.startswith("| T018 "))
    t019_row = next(line for line in todo.splitlines() if line.startswith("| T019 "))
    t020_row = next(line for line in todo.splitlines() if line.startswith("| T020 "))
    assert t013_row.endswith("| Done |")
    assert t014_row.endswith("| Done |")
    assert t015_row.endswith("| Done |")
    assert t016_row.endswith("| Done |")
    assert t017_row.endswith("| Done |")
    assert t018_row.endswith("| Done |")
    assert t019_row.endswith("| Done |")
    assert t020_row.endswith("| Todo |")
    assert "go-primary-notes-delete-parity.json" in todo
    assert "T013 Go notes delete parity gate is complete" in architecture
    assert "Go T013" in schema
    assert "delete/batch-delete parity" in readme
    assert "T013" in go_report
    assert "does not promote live/default notes write ownership" in architecture
