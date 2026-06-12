import io
import json
import os
import shutil
import socket
import sqlite3
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path

import pytest

from tests.go_primary_parity_harness import build_go_shadow_exe


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"
GO_MAIN_PATH = GO_SHADOW_DIR / "main.go"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
GO_README_PATH = GO_SHADOW_DIR / "README.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
CONTRACTS = {
    "T020": ROOT / "docs" / "contracts" / "go-primary-attachment-raw-serving-parity.json",
    "T021": ROOT / "docs" / "contracts" / "go-primary-upload-parity.json",
    "T022": ROOT / "docs" / "contracts" / "go-primary-thumbnail-generation-parity.json",
    "T023": ROOT / "docs" / "contracts" / "go-primary-upload-url-parity.json",
}


def _png_bytes(width=1, height=1):
    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + (b"\xff\x00\x00" * width) for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


PNG_1X1 = _png_bytes()


def _copy_db(src, dst):
    shutil.copyfile(src, dst)
    return str(dst)


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _tree_bytes(root):
    root = Path(root)
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def _request_json(base, path, *, method="GET"):
    request = urllib.request.Request(base.rstrip("/") + path, method=method)
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


def _request_bytes(base, path, *, headers=None):
    request = urllib.request.Request(base.rstrip("/") + path, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def _multipart_body(filename, content, *, thumbnail_only="false"):
    boundary = f"prism-t021-{time.time_ns()}"
    chunks = [
        f"--{boundary}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"),
        b"Content-Type: application/octet-stream\r\n\r\n",
        content,
        b"\r\n",
        f"--{boundary}\r\n".encode("utf-8"),
        b'Content-Disposition: form-data; name="thumbnail_only"\r\n\r\n',
        str(thumbnail_only).encode("utf-8"),
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    return boundary, b"".join(chunks)


def _request_upload(base, filename, content, *, thumbnail_only="false"):
    boundary, body = _multipart_body(filename, content, thumbnail_only=thumbnail_only)
    request = urllib.request.Request(base.rstrip("/") + "/api/upload", data=body, method="POST")
    request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _start_go(db_path, data_dir, tmp_path, *flags):
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
        *flags,
    ]
    proc = subprocess.Popen(
        args,
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
    pytest.fail(f"Go T020-T023 candidate did not start:\n{output}")


def _seed_raw_attachment_fixture(db_path, data_root):
    attachments_dir = Path(data_root) / "docs" / "attachments"
    uploads_dir = Path(data_root) / "static" / "uploads"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    (attachments_dir / "t020-text.md").write_text("raw text fixture\nsecond line", encoding="utf-8")
    (attachments_dir / "t020-image.png").write_bytes(PNG_1X1)
    (attachments_dir / "t020-unsupported.exe").write_bytes(b"MZ-not-allowed")

    conn = sqlite3.connect(db_path)
    try:
        note_id = conn.execute("SELECT id FROM Notes ORDER BY id LIMIT 1").fetchone()[0]
        ids = {}
        rows = [
            ("text", "docs/attachments/t020-text.md", "md", "T020 Text", 24),
            ("binary", "docs/attachments/t020-image.png", "png", "T020 Binary", len(PNG_1X1)),
            ("missing", "docs/attachments/t020-missing.md", "md", "T020 Missing", 0),
            ("unsafe", "../outside.md", "md", "T020 Unsafe", 0),
            ("unsupported", "docs/attachments/t020-unsupported.exe", "exe", "T020 Unsupported", 14),
        ]
        for key, file_path, file_type, title, size in rows:
            cursor = conn.execute(
                """
                INSERT INTO Note_Attachments
                    (note_id, file_path, file_type, title, size_bytes, is_auto_extracted)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (note_id, file_path, file_type, title, size),
            )
            ids[key] = cursor.lastrowid
        conn.commit()
        return ids
    finally:
        conn.close()


def _load_contract(task_id):
    return json.loads(CONTRACTS[task_id].read_text(encoding="utf-8"))


def test_t020_attachment_raw_text_binary_range_and_safety_cases(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t020.db")
    go_data = tmp_path / "go_data"
    ids = _seed_raw_attachment_fixture(go_db, go_data)
    attachments_before = _tree_bytes(go_data / "docs" / "attachments")
    uploads_before = _tree_bytes(go_data / "static" / "uploads")

    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-attachment-raw-read")
    try:
        status, health = _request_json(base, "/healthz")
        assert status == 200
        assert health["runtime"]["api_surface"] == "get-read-only+local-attachment-raw-read"
        assert health["runtime"]["sqlite_query_only"] is True

        status, payload = _request_json(base, f"/api/attachments/{ids['text']}")
        assert status == 200
        assert payload["data"]["content"] == "raw text fixture\nsecond line"

        status, headers, body = _request_bytes(base, f"/api/attachments/{ids['text']}?raw=true")
        assert status == 200
        expected_text_bytes = (go_data / "docs" / "attachments" / "t020-text.md").read_bytes()
        assert body == expected_text_bytes
        assert headers["Content-Type"].startswith("text/markdown")

        status, headers, body = _request_bytes(
            base,
            f"/api/attachments/{ids['text']}?raw=true",
            headers={"Range": "bytes=0-6"},
        )
        assert status == 206
        assert body == expected_text_bytes[:7]
        assert headers["Content-Range"].startswith("bytes 0-6/")

        status, headers, body = _request_bytes(base, f"/api/attachments/{ids['binary']}?raw=true")
        assert status == 200
        assert body == PNG_1X1
        assert headers["Content-Type"].startswith("image/png")

        for key in ("missing", "unsafe", "unsupported"):
            status, payload = _request_json(base, f"/api/attachments/{ids[key]}?raw=true")
            assert status == 404
            assert payload == {"status": "error", "message": "File not found on disk"}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert _tree_bytes(go_data / "docs" / "attachments") == attachments_before
    assert _tree_bytes(go_data / "static" / "uploads") == uploads_before


def test_t021_t022_upload_writes_originals_webp_thumbnails_and_rolls_back_failures(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t021_t022.db")
    go_data = tmp_path / "go_data"

    proc, base = _start_go(
        go_db,
        go_data,
        tmp_path,
        "--enable-upload-write",
        "--enable-thumbnail-write",
    )
    try:
        status, health = _request_json(base, "/healthz")
        assert status == 200
        assert health["runtime"]["api_surface"] == "get-read-only+local-upload-write+local-thumbnail-write"
        assert health["runtime"]["sqlite_query_only"] is True

        uploads_dir = go_data / "static" / "uploads"

        for ext in ("jpg", "png", "webp", "gif"):
            status, payload = _request_upload(base, f"fixture.{ext}", PNG_1X1, thumbnail_only="false")
            assert status == 200
            assert payload["status"] == "success"
            filename = payload["data"]["filename"]
            assert filename.endswith(f".{ext}")
            assert payload["data"]["url"] == f"/static/uploads/{filename}"
            assert (uploads_dir / filename).read_bytes() == PNG_1X1
            thumb = uploads_dir / f"{Path(filename).stem}_thumb.webp"
            assert thumb.read_bytes().startswith(b"RIFF")
            assert b"WEBP" in thumb.read_bytes()[:16]

        status, payload = _request_upload(base, "../../evil.png", PNG_1X1, thumbnail_only="false")
        assert status == 200
        assert "/../" not in payload["data"]["url"]
        assert payload["data"]["filename"].endswith("_evil.png")

        before_failure = _tree_bytes(uploads_dir)
        for filename, content in (
            ("bad.png", b"not an image"),
            ("bad.exe", PNG_1X1),
            ("huge.png", b"\x89PNG\r\n\x1a\n" + (b"x" * (5 * 1024 * 1024))),
        ):
            status, payload = _request_upload(base, filename, content, thumbnail_only="false")
            assert status == 400
            assert payload["status"] == "error"
            assert _tree_bytes(uploads_dir) == before_failure

        status, payload = _request_upload(base, "thumb-only.png", PNG_1X1, thumbnail_only="true")
        assert status == 200
        thumb_only_name = payload["data"]["filename"]
        assert thumb_only_name.endswith("_thumb.webp")
        assert (uploads_dir / thumb_only_name).exists()
        assert not (uploads_dir / thumb_only_name.replace("_thumb.webp", ".png")).exists()
        assert payload["data"]["thumbnail_only"] is True
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_t023_upload_url_and_thumbnail_go_unit_fixtures_cover_remote_safety():
    result = subprocess.run(
        [
            "go",
            "test",
            "./...",
            "-run",
            "TestUploadURL|TestThumbnail|TestStandardThumbnailUpload|TestThumbnailOnlyUpload",
        ],
        cwd=GO_SHADOW_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_t020_t023_contracts_docs_and_active_queue_are_closed():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    expected = {
        "T020": ("CONTRACT-GO-PRIMARY-FILES", "completed_local_candidate", "--enable-attachment-raw-read"),
        "T021": ("CONTRACT-GO-PRIMARY-UPLOADS", "completed_local_candidate", "--enable-upload-write"),
        "T022": ("CONTRACT-GO-PRIMARY-UPLOADS", "completed_local_candidate", "--enable-thumbnail-write"),
        "T023": ("CONTRACT-GO-PRIMARY-UPLOADS", "completed_local_candidate", "--enable-upload-url-write"),
    }
    for task_id, (contract_name, status, flag) in expected.items():
        contract = _load_contract(task_id)
        assert contract["task_id"] == task_id
        assert contract["contract"] == contract_name
        assert contract["status"] == status
        assert contract["enable_flag"] == flag
        assert contract["runtime_boundary"]["production_db_write"] is False
        assert contract["runtime_boundary"]["production_filesystem_mutation"] is False
        assert contract["runtime_boundary"]["pi_deploy"] is False
        assert Path(contract["validation"]["targeted_tests"][0]).name == Path(__file__).name
        row = next(line for line in todo.splitlines() if line.startswith(f"| {task_id} "))
        assert row.endswith("| Done |")

    assert '"enable-attachment-raw-read"' in main_go
    assert "PRISM_GO_ENABLE_ATTACHMENT_RAW_READ" in main_go
    assert '"enable-upload-write"' in main_go
    assert "PRISM_GO_ENABLE_UPLOAD_WRITE" in main_go
    assert "http.ServeContent" in main_go
    assert "validateUploadURLTarget" in main_go

    assert "T020-T023 Go files/uploads gates 已完成" in todo
    assert "T020-T023 Go files/uploads local candidates are complete" in architecture
    assert "Go T020-T023" in schema
    assert "Attachments Raw Serving And Uploads" in readme
    assert "T020-T023" in go_report
    assert "T024" in _load_contract("T023")["allowed_next_step"]["id"]
