import base64
import io
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

import pytest

from tests.go_primary_parity_harness import build_go_shadow_exe


ROOT = Path(__file__).resolve().parents[1]
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
GO_README_PATH = ROOT / "go-shadow" / "README.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"
ROUTE_MANIFEST_PATH = ROOT / "docs" / "contracts" / "go-primary-route-ownership-manifest.json"
CONTRACTS = {
    "T028": ROOT / "docs" / "contracts" / "go-primary-markdown-import-parity.json",
    "T029": ROOT / "docs" / "contracts" / "go-primary-json-import-parity.json",
    "T030": ROOT / "docs" / "contracts" / "go-primary-json-markdown-export-parity.json",
    "T031": ROOT / "docs" / "contracts" / "go-primary-db-images-export-parity.json",
}
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/axpZ3QAAAAASUVORK5CYII="
)


def _copy_db(src, dst):
    shutil.copyfile(src, dst)
    return str(dst)


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_go(db_path, data_dir, tmp_path, *flags):
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
            *flags,
        ],
        env=dict(os.environ),
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
    pytest.fail(f"Go T028-T031 candidate did not start:\n{output}")


def _stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _request_bytes(base, path, *, method="GET", data=None, headers=None):
    body = data
    request_headers = dict(headers or {})
    if isinstance(data, dict):
        body = json.dumps(data).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        base.rstrip("/") + path,
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def _request_json(base, path, *, method="GET", data=None):
    status, headers, body = _request_bytes(base, path, method=method, data=data)
    try:
        payload = json.loads(body.decode("utf-8")) if body else None
    except json.JSONDecodeError:
        payload = body.decode("utf-8", errors="replace")
    return status, payload, headers


def _request_multipart(base, path, files):
    boundary = f"----prism-{uuid.uuid4().hex}"
    body = io.BytesIO()
    for field, filename, content, content_type in files:
        body.write(f"--{boundary}\r\n".encode("ascii"))
        body.write(
            (
                f'Content-Disposition: form-data; name="{field}"; '
                f'filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8")
        )
        body.write(content)
        body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode("ascii"))
    status, headers, payload = _request_bytes(
        base,
        path,
        method="POST",
        data=body.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        parsed = json.loads(payload.decode("utf-8")) if payload else None
    except json.JSONDecodeError:
        parsed = payload.decode("utf-8", errors="replace")
    return status, parsed, headers


def _query_one(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _query_all(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _write_upload(data_dir, filename, content=PNG_1X1):
    upload_dir = Path(data_dir) / "static" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / filename
    target.write_bytes(content)
    return target


def _seed_export_fixture(db_path, data_dir):
    _write_upload(data_dir, "export-image.png", PNG_1X1)
    attachments = Path(data_dir) / "docs" / "attachments"
    attachments.mkdir(parents=True, exist_ok=True)
    (attachments / "export.md").write_text("attachment body", encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            UPDATE Notes
            SET title = 'Export Source',
                content = 'Body ![img](/static/uploads/export-image.png)\n<img src="/static/uploads/export-image.png">',
                cover_image = '/static/uploads/export-image.png'
            WHERE id = 1
            """
        )
        conn.execute(
            """
            INSERT INTO Note_Attachments
                (note_id, file_path, file_type, title, size_bytes, is_auto_extracted)
            VALUES (1, 'docs/attachments/export.md', 'md', 'export', 15, 0)
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_t028_markdown_import_flag_gate_and_fixture(temp_db, tmp_path):
    disabled_db = _copy_db(temp_db, tmp_path / "go_t028_disabled.db")
    disabled_data = tmp_path / "disabled_data"
    proc, base = _start_go(disabled_db, disabled_data, tmp_path)
    try:
        status, payload, _ = _request_json(base, "/healthz")
        assert status == 200
        assert payload["runtime"]["api_surface"] == "get-read-only"
        assert payload["runtime"]["sqlite_query_only"] is True

        status, payload, _ = _request_multipart(
            base,
            "/api/notes/import/md",
            [("file", "blocked.md", b"# Blocked", "text/markdown")],
        )
        assert status == 405
        assert payload["message"] == "Import/export route is disabled"
    finally:
        _stop(proc)

    go_db = _copy_db(temp_db, tmp_path / "go_t028.db")
    go_data = tmp_path / "go_data"
    _write_upload(go_data, "existing.png")
    markdown = """---
category: 筆記
tags: [alpha, beta]
source_urls: [https://source.example/a]
---
# Imported Markdown

Body ![keep](/static/uploads/existing.png)
![local](local.png)
![missing](missing.png)
"""
    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-import-export")
    try:
        status, payload, _ = _request_json(base, "/healthz")
        assert status == 200
        assert payload["runtime"]["api_surface"] == "get-read-only+local-import-export"
        assert payload["runtime"]["sqlite_query_only"] is False

        status, payload, _ = _request_multipart(
            base,
            "/api/notes/import/md",
            [
                ("file", "import.md", markdown.encode("utf-8"), "text/markdown"),
                ("images", "local.png", PNG_1X1, "image/png"),
            ],
        )
        assert status == 201
        note_id = payload["data"]["note_id"]
        note = _query_one(go_db, "SELECT title, content FROM Notes WHERE id = ?", (note_id,))
        assert note["title"] == "Imported Markdown"
        assert "/static/uploads/existing.png" in note["content"]
        assert "![local](local.png)" not in note["content"]
        assert "[missing]" in note["content"]
        assert len(list((go_data / "static" / "uploads").glob("*local.png"))) >= 1

        tags = {
            row["name"]
            for row in _query_all(
                go_db,
                """
                SELECT t.name FROM Tags t
                JOIN Note_Tags nt ON nt.tag_id = t.id
                WHERE nt.note_id = ?
                """,
                (note_id,),
            )
        }
        assert {"alpha", "beta"} <= tags
        urls = _query_all(go_db, "SELECT url FROM Source_Urls WHERE note_id = ?", (note_id,))
        assert urls == [{"url": "https://source.example/a"}]
    finally:
        _stop(proc)


def test_t029_json_import_duplicate_skip_and_rollback(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t029.db")
    go_data = tmp_path / "go_data"
    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-import-export")
    try:
        status, payload, _ = _request_json(
            base,
            "/api/import/json",
            method="POST",
            data={
                "mode": "skip",
                "data": {
                    "notes": [
                        {"id": 10, "title": "Welcome Note", "content": "Welcome to Prism!"},
                        {
                            "id": 11,
                            "title": "JSON Imported",
                            "content": "json body",
                            "category": "筆記",
                            "tags": ["json-tag"],
                            "urls": ["https://source.example/json"],
                        },
                    ]
                },
            },
        )
        assert status == 200
        assert payload["data"]["imported"] == 1
        assert payload["data"]["skipped"] == 1
        assert payload["data"]["duplicates"] == ["Welcome Note"]
        imported = _query_one(go_db, "SELECT id FROM Notes WHERE title = 'JSON Imported'")
        assert imported is not None

        before_count = _query_one(go_db, "SELECT COUNT(*) AS count FROM Notes")["count"]
        status, payload, _ = _request_json(
            base,
            "/api/import/json",
            method="POST",
            data={
                "data": {
                    "notes": [{"id": 900, "title": "Rollback Candidate", "content": "rollback body"}],
                    "attachments": [
                        {
                            "note_id": 900,
                            "file_path": "docs/attachments/rollback.md",
                            "file_type": "md",
                            "content_b64": "not-valid-base64",
                        }
                    ],
                }
            },
        )
        assert status == 400
        assert "invalid attachment content_b64" in payload["message"]
        after_count = _query_one(go_db, "SELECT COUNT(*) AS count FROM Notes")["count"]
        assert after_count == before_count
        assert _query_one(go_db, "SELECT id FROM Notes WHERE title = 'Rollback Candidate'") is None
        assert not (go_data / "docs" / "attachments" / "rollback.md").exists()
    finally:
        _stop(proc)


def test_t030_t031_export_json_markdown_db_images_and_batch(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t030_t031.db")
    go_data = tmp_path / "go_data"
    _seed_export_fixture(go_db, go_data)
    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-import-export")
    try:
        status, _, body = _request_bytes(base, "/api/export/json")
        assert status == 200
        export_payload = json.loads(body.decode("utf-8"))
        assert export_payload["export_info"]["notes_count"] >= 1
        assert export_payload["categories"]
        assert export_payload["attachments"][0]["file_path"] == "docs/attachments/export.md"
        assert any(item["filename"] == "export-image.png" for item in export_payload["uploads"])

        status, _, body = _request_bytes(base, "/api/export/markdown")
        assert status == 200
        markdown_zip = zipfile.ZipFile(io.BytesIO(body))
        assert "_manifest.json" in markdown_zip.namelist()
        assert "images/export-image.png" in markdown_zip.namelist()
        md_names = [name for name in markdown_zip.namelist() if name.endswith(".md")]
        md_text = "\n".join(markdown_zip.read(name).decode("utf-8") for name in md_names)
        assert "/static/uploads/export-image.png" not in md_text
        assert "images/export-image.png" in md_text

        status, _, body = _request_bytes(base, "/api/export/db")
        assert status == 200
        assert body.startswith(b"SQLite format 3")

        status, _, body = _request_bytes(
            base,
            "/api/export/images",
            method="POST",
            data={"images": ["/static/uploads/export-image.png"], "note_title": "Export Source"},
        )
        assert status == 200
        image_zip = zipfile.ZipFile(io.BytesIO(body))
        assert "export-image.png" in image_zip.namelist()
        assert image_zip.read("export-image.png") == PNG_1X1

        status, _, body = _request_bytes(
            base,
            "/api/notes/export/batch",
            method="POST",
            data={"note_ids": [1]},
        )
        assert status == 200
        batch_zip = zipfile.ZipFile(io.BytesIO(body))
        assert any(name.startswith("notes/") and name.endswith(".md") for name in batch_zip.namelist())
        assert "assets/export-image.png" in batch_zip.namelist()
    finally:
        _stop(proc)


def test_t028_t031_docs_and_contracts_are_updated():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    assert "enable-import-export" in main_go
    assert "PRISM_GO_ENABLE_IMPORT_EXPORT" in main_go
    assert "local-import-export" in main_go

    todo = TODO_PATH.read_text(encoding="utf-8")
    for task_id in ("T028", "T029", "T030", "T031"):
        row = next(line for line in todo.splitlines() if line.startswith(f"| {task_id} |"))
        assert row.endswith("| Done |")

    for path in (ARCHITECTURE_PATH, SCHEMA_PATH, GO_README_PATH, GO_REPORT_PATH):
        text = path.read_text(encoding="utf-8")
        assert "T028-T031" in text
        assert "local/copied" in text
        assert "production" in text.lower() or "正式" in text

    manifest = json.loads(ROUTE_MANIFEST_PATH.read_text(encoding="utf-8"))
    candidates = {
        route["rule"]: route.get("go_candidate")
        for route in manifest["routes"]
        if route["rule"]
        in {
            "/api/notes/import/md",
            "/api/import/json",
            "/api/export/json",
            "/api/export/markdown",
            "/api/export/db",
            "/api/export/images",
            "/api/notes/export/batch",
        }
    }
    assert set(candidates) == {
        "/api/notes/import/md",
        "/api/import/json",
        "/api/export/json",
        "/api/export/markdown",
        "/api/export/db",
        "/api/export/images",
        "/api/notes/export/batch",
    }
    assert all("local copied" in value for value in candidates.values())

    for task_id, path in CONTRACTS.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["task_id"] == task_id
        assert payload["status"] == "completed"
        assert "production" in json.dumps(payload, ensure_ascii=False).lower()
