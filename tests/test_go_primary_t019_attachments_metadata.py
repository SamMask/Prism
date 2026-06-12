import io
import json
import os
import re
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
CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-attachments-metadata-parity.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
GO_README_PATH = GO_SHADOW_DIR / "README.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"
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


def _multipart_body(fields=None, files=None):
    boundary = f"prism-t019-{time.time_ns()}"
    chunks = []
    for name, value in (fields or {}).items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    for name, filename, content, content_type in (files or []):
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                content,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return boundary, b"".join(chunks)


def _request_multipart(base, path, *, fields=None, files=None, method="POST"):
    boundary, body = _multipart_body(fields=fields, files=files)
    request = urllib.request.Request(base.rstrip("/") + path, data=body, method=method)
    request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
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


def _start_go(db_path, data_dir, tmp_path, *, attachment_write=False, attachment_text=False):
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
    if attachment_write:
        args.append("--enable-attachment-write")
        env["PRISM_GO_ENABLE_ATTACHMENT_WRITE"] = "1"
    if attachment_text:
        args.append("--enable-attachment-text-read")
        env["PRISM_GO_ENABLE_ATTACHMENT_TEXT_READ"] = "1"

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
    pytest.fail(f"Go T019 candidate did not start:\n{output}")


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


def _seed_t019_fixture(db_path, data_root):
    attachments_dir = Path(data_root) / "docs" / "attachments"
    uploads_dir = Path(data_root) / "static" / "uploads"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / "keep.txt").write_text("uploads unchanged", encoding="utf-8")
    (attachments_dir / "t019-list.md").write_text("list fixture", encoding="utf-8")
    (attachments_dir / "t019-delete.md").write_text("delete fixture", encoding="utf-8")

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        category_id = conn.execute("SELECT id FROM Categories WHERE is_default = 1 LIMIT 1").fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO Notes (title, content, remarks, category_id)
            VALUES ('T019 Attachment Note', 'attachment body', 't019 fixture', ?)
            """,
            (category_id,),
        )
        note_id = cursor.lastrowid
        other_note_id = conn.execute(
            """
            INSERT INTO Notes (title, content, remarks, category_id)
            VALUES ('T019 Empty Attachments', 'empty body', 't019 fixture', ?)
            """,
            (category_id,),
        ).lastrowid
        rows = [
            ("docs/attachments/t019-list.md", "md", "T019 List", 12, 0, "2026-01-01 00:00:01"),
            ("docs/attachments/t019-delete.md", "md", "T019 Delete", 14, 0, "2026-01-01 00:00:02"),
            ("docs/attachments/t019-missing.md", "md", "T019 Missing File", 0, 0, "2026-01-01 00:00:03"),
        ]
        ids = {"note": note_id, "empty_note": other_note_id}
        for key, row in zip(("list", "delete", "missing_file"), rows):
            cursor = conn.execute(
                """
                INSERT INTO Note_Attachments
                    (note_id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (note_id, *row),
            )
            ids[key] = cursor.lastrowid
        conn.commit()
        return ids
    finally:
        conn.close()


def _tree_bytes(root):
    root = Path(root)
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def _snapshot(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return {
            "attachments": conn.execute(
                """
                SELECT id, note_id, file_path, file_type, title, size_bytes, COALESCE(is_auto_extracted, 0), created_at
                FROM Note_Attachments
                ORDER BY id
                """
            ).fetchall(),
            "notes": conn.execute("SELECT id, title, content FROM Notes ORDER BY id").fetchall(),
        }
    finally:
        conn.close()


def _normalize_timestamped_path(value):
    if not isinstance(value, str):
        return value
    return re.sub(r"_\d{8}_\d{6}(?=\.[^./\\]+$)", "_TIMESTAMP", value)


def _normalize_payload(value):
    if isinstance(value, list):
        return [_normalize_payload(item) for item in value]
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key == "file_path":
                out[key] = _normalize_timestamped_path(item)
            elif key == "created_at":
                out[key] = "<created_at>"
            else:
                out[key] = _normalize_payload(item)
        return out
    return value


def _normalize_snapshot(snapshot):
    return {
        "attachments": [
            tuple(
                _normalize_timestamped_path(value) if index == 2 else "<created_at>" if index == 7 else value
                for index, value in enumerate(row)
            )
            for row in snapshot["attachments"]
        ],
        "notes": snapshot["notes"],
    }


def test_t019_contract_records_local_candidate_boundaries():
    contract = _load_json(CONTRACT_PATH)
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")

    assert contract["task_id"] == "T019"
    assert contract["status"] == "completed_local_candidate"
    assert contract["covered_routes"] == [
        "GET /api/notes/<id>/attachments",
        "POST /api/notes/<id>/attachments",
        "DELETE /api/attachments/<id>",
    ]
    assert contract["update_route_boundary"]["PUT /api/attachments/<id>"] == "not a current Python API route"
    assert contract["runtime_boundary"]["production_db_write"] is False
    assert contract["runtime_boundary"]["production_filesystem_mutation"] is False
    assert contract["runtime_boundary"]["go_default_write_owner"] is False
    assert "enable-attachment-write" in main_go
    assert "PRISM_GO_ENABLE_ATTACHMENT_WRITE" in main_go
    assert "listNoteAttachments" in main_go
    assert "uploadAttachment" in main_go
    assert "deleteAttachment" in main_go
    assert "enableAttachmentTextRead" in main_go


def test_t019_go_attachment_metadata_upload_and_delete_match_python_response_db_and_files(temp_db, tmp_path):
    py_db = _copy_db(temp_db, tmp_path / "python_t019.db")
    go_db = _copy_db(temp_db, tmp_path / "go_t019.db")
    py_data = tmp_path / "python_data"
    go_data = tmp_path / "go_data"
    py_ids = _seed_t019_fixture(py_db, py_data)
    go_ids = _seed_t019_fixture(go_db, go_data)
    assert py_ids == go_ids

    client, ctx = _flask_client(py_db, py_data)
    proc, base = _start_go(go_db, go_data, tmp_path, attachment_write=True)
    try:
        health_status, health_json = _request_json(base, "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only+local-attachment-write"
        assert health_json["runtime"]["sqlite_query_only"] is False

        path = f"/api/notes/{py_ids['note']}/attachments"
        py_response = client.get(path)
        go_status, go_json = _request_json(base, path)
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        py_response = client.get("/api/notes/999999/attachments")
        go_status, go_json = _request_json(base, "/api/notes/999999/attachments")
        assert go_status == py_response.status_code == 404
        assert go_json == py_response.get_json()

        before_py = _normalize_snapshot(_snapshot(py_db))
        before_go = _normalize_snapshot(_snapshot(go_db))
        py_response = client.post(f"/api/notes/{py_ids['note']}/attachments", data={"title": "No File"})
        go_status, go_json = _request_multipart(
            base,
            f"/api/notes/{go_ids['note']}/attachments",
            fields={"title": "No File"},
        )
        assert go_status == py_response.status_code == 400
        assert go_json == py_response.get_json()
        assert _normalize_snapshot(_snapshot(py_db)) == before_py
        assert _normalize_snapshot(_snapshot(go_db)) == before_go

        bad_file = {"file": (io.BytesIO(b"bad"), "bad.exe")}
        py_response = client.post(
            f"/api/notes/{py_ids['note']}/attachments",
            data=bad_file,
            content_type="multipart/form-data",
        )
        go_status, go_json = _request_multipart(
            base,
            f"/api/notes/{go_ids['note']}/attachments",
            files=[("file", "bad.exe", b"bad", "application/octet-stream")],
        )
        assert go_status == py_response.status_code == 400
        assert go_json == py_response.get_json()
        assert _normalize_snapshot(_snapshot(py_db)) == before_py
        assert _normalize_snapshot(_snapshot(go_db)) == before_go

        upload_bytes = b"# T019 Upload\nhello"
        py_response = client.post(
            f"/api/notes/{py_ids['note']}/attachments",
            data={"title": "Uploaded Title", "file": (io.BytesIO(upload_bytes), "T019 Upload.md")},
            content_type="multipart/form-data",
        )
        go_status, go_json = _request_multipart(
            base,
            f"/api/notes/{go_ids['note']}/attachments",
            fields={"title": "Uploaded Title"},
            files=[("file", "T019 Upload.md", upload_bytes, "text/markdown")],
        )
        assert go_status == py_response.status_code == 200
        assert _normalize_payload(go_json) == _normalize_payload(py_response.get_json())
        assert go_json["data"]["size_bytes"] == len(upload_bytes)
        assert (go_data / go_json["data"]["file_path"]).read_bytes() == upload_bytes
        assert (py_data / py_response.get_json()["data"]["file_path"]).read_bytes() == upload_bytes

        py_response = client.get(path)
        go_status, go_json = _request_json(base, path)
        assert go_status == py_response.status_code == 200
        assert _normalize_payload(go_json) == _normalize_payload(py_response.get_json())

        py_response = client.delete(f"/api/attachments/{py_ids['delete']}")
        go_status, go_json = _request_json(base, f"/api/attachments/{go_ids['delete']}", method="DELETE")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
        assert not (py_data / "docs" / "attachments" / "t019-delete.md").exists()
        assert not (go_data / "docs" / "attachments" / "t019-delete.md").exists()

        py_response = client.delete(f"/api/attachments/{py_ids['missing_file']}")
        go_status, go_json = _request_json(base, f"/api/attachments/{go_ids['missing_file']}", method="DELETE")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        py_response = client.delete("/api/attachments/999999")
        go_status, go_json = _request_json(base, "/api/attachments/999999", method="DELETE")
        assert go_status == py_response.status_code == 404
        assert go_json == py_response.get_json()

        py_response = client.put(f"/api/attachments/{py_ids['list']}", json={"title": "No update route"})
        go_status, _ = _request_json(
            base,
            f"/api/attachments/{go_ids['list']}",
            data={"title": "No update route"},
            method="PUT",
        )
        assert go_status == py_response.status_code == 405

        py_response = client.put(f"/api/notes/{py_ids['note']}/attachments", json={"title": "No update route"})
        go_status, _ = _request_json(
            base,
            f"/api/notes/{go_ids['note']}/attachments",
            data={"title": "No update route"},
            method="PUT",
        )
        assert go_status == py_response.status_code == 405
    finally:
        ctx.pop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert _normalize_snapshot(_snapshot(go_db)) == _normalize_snapshot(_snapshot(py_db))
    assert _tree_bytes(go_data / "static" / "uploads") == _tree_bytes(py_data / "static" / "uploads")


def test_t019_default_runtime_keeps_attachment_writes_disabled(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t019_disabled.db")
    go_data = tmp_path / "go_data"
    ids = _seed_t019_fixture(go_db, go_data)
    before_db = _normalize_snapshot(_snapshot(go_db))
    before_attachments = _tree_bytes(go_data / "docs" / "attachments")
    before_uploads = _tree_bytes(go_data / "static" / "uploads")

    proc, base = _start_go(go_db, go_data, tmp_path)
    try:
        health_status, health_json = _request_json(base, "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only"
        assert health_json["runtime"]["sqlite_query_only"] is True

        status, payload = _request_json(base, f"/api/notes/{ids['note']}/attachments")
        assert status == 405
        assert payload["message"] == "Attachment write route is disabled"

        status, payload = _request_multipart(
            base,
            f"/api/notes/{ids['note']}/attachments",
            fields={"title": "Blocked"},
            files=[("file", "blocked.md", b"blocked", "text/markdown")],
        )
        assert status == 405
        assert payload["message"] == "Attachment write route is disabled"

        status, payload = _request_json(base, f"/api/attachments/{ids['delete']}", method="DELETE")
        assert status == 405
        assert payload["message"] == "Attachment write route is disabled"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert _normalize_snapshot(_snapshot(go_db)) == before_db
    assert _tree_bytes(go_data / "docs" / "attachments") == before_attachments
    assert _tree_bytes(go_data / "static" / "uploads") == before_uploads


def test_t019_docs_mark_done_and_keep_runtime_boundaries():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    t019_row = next(line for line in todo.splitlines() if line.startswith("| T019 "))
    t020_row = next(line for line in todo.splitlines() if line.startswith("| T020 "))
    assert t019_row.endswith("| Done |")
    assert t020_row.endswith("| Done |")
    assert "go-primary-attachments-metadata-parity.json" in todo
    assert "T019 Go attachments metadata gate is complete" in architecture
    assert "Go T019" in schema
    assert "Attachments Metadata Upload/Delete" in readme
    assert "T019" in go_report
    assert "does not promote live/default files ownership" in architecture
