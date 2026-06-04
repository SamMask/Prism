import json
import os
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"
VOLATILE_KEYS = {"created_at", "updated_at"}
CASES = [
    "/api/test",
    "/api/categories",
    "/api/tags",
    "/api/notes?page=1&per_page=20",
    "/api/notes?page=999&per_page=20",
    "/api/notes?page=1&per_page=1",
    "/api/notes?page=1&per_page=500",
    "/api/notes?page=1&per_page=20&include_archived=true",
    "/api/notes?page=1&per_page=20&pinned_only=true",
    "/api/notes?page=1&per_page=20&sort=created",
    "/api/notes?page=1&per_page=20&sort=custom",
    "/api/notes?page=1&per_page=20&type=%E7%AD%86%E8%A8%98",
    "/api/notes?page=1&per_page=20&tags=1&tag_mode=OR",
    "/api/notes?page=1&per_page=20&tags=1&tag_mode=AND",
    "/api/notes/1",
    "/api/notes/999999",
    "/api/notes?q=Welcome&page=1&per_page=20",
    "/api/notes?q=todo.md&page=1&per_page=20",
    "/api/notes?q=%E4%B8%AD%E6%96%87%E6%90%9C%E5%B0%8B&page=1&per_page=20",
    "/api/notes?q=attachment-meta-canary&page=1&per_page=20",
    "/api/notes?q=no-such-canary-result&page=1&per_page=20",
    "/api/notes?category_id=1&page=1&per_page=20",
]


def _normalize(value):
    if isinstance(value, dict):
        return {
            key: "<timestamp>" if key in VOLATILE_KEYS and item is not None else _normalize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _read_json(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _seed_diff_matrix_data(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('matrix-tag')")
        tag_id = conn.execute(
            "SELECT id FROM Tags WHERE name = 'matrix-tag'"
        ).fetchone()[0]
        category_id = conn.execute(
            "SELECT id FROM Categories WHERE is_default = 1 LIMIT 1"
        ).fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO Notes (
                title, content, category_id, is_pinned, sort_order, remarks
            ) VALUES (?, ?, ?, 1, 999, ?)
            """,
            (
                "中文搜尋 todo.md Canary",
                "這是一筆中文搜尋內容，包含 todo.md 和 canary matrix",
                category_id,
                "phase19 read-only diff seed",
            ),
        )
        note_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)",
            (note_id, tag_id),
        )
        conn.execute(
            """
            INSERT INTO Note_Attachments (
                note_id, file_path, file_type, title, size_bytes
            ) VALUES (?, ?, 'md', ?, 128)
            """,
            (
                note_id,
                "docs/attachments/attachment-meta-canary.md",
                "attachment-meta-canary reference",
            ),
        )
        conn.commit()
        return category_id, tag_id
    finally:
        conn.close()


def test_go_shadow_scaffold_is_read_only():
    main_go = (GO_SHADOW_DIR / "main.go").read_text(encoding="utf-8")

    assert (GO_SHADOW_DIR / "go.mod").exists()
    assert "expectedSchemaVersion = 16" in main_go
    assert "PRAGMA query_only = ON" in main_go
    assert "PRAGMA query_only" in main_go
    assert "refusing to open production-like database" in main_go
    assert '"/healthz"' in main_go
    assert '"/api/test"' in main_go
    assert '"/api/categories"' in main_go
    assert '"/api/tags"' in main_go
    assert '"/api/notes"' in main_go
    assert "http.MethodGet" in main_go
    assert "http.MethodPost" not in main_go
    assert "http.MethodPut" not in main_go
    assert "http.MethodDelete" not in main_go


def test_go_shadow_python_response_diff(client, temp_db):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; scaffold/static read-only checks still run.")

    category_id, tag_id = _seed_diff_matrix_data(temp_db)
    cases = CASES + [
        (
            f"/api/notes?page=1&per_page=20&category_id={category_id}"
            f"&tags={tag_id}&tag_mode=OR&sort=created"
        )
    ]

    port = _free_port()
    data_dir = tempfile.mkdtemp(prefix="prism-go-runtime-")
    env = os.environ.copy()
    env["PRISM_GO_DB"] = temp_db
    env["PRISM_GO_ADDR"] = f"127.0.0.1:{port}"
    proc = subprocess.Popen(
        [
            go_bin,
            "run",
            ".",
            "--db",
            temp_db,
            "--addr",
            f"127.0.0.1:{port}",
            "--data-dir",
            data_dir,
        ],
        cwd=GO_SHADOW_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                _read_json(base + "/api/test")
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.25)
        else:
            output = proc.stdout.read() if proc.stdout else ""
            pytest.fail(f"Go shadow server did not start:\n{output}")

        health_status, health_json = _read_json(base + "/healthz")
        assert health_status == 200
        assert health_json["status"] == "ok"
        assert health_json["runtime"]["api_surface"] == "get-read-only"
        assert health_json["runtime"]["schema_version"] >= 16
        assert health_json["runtime"]["sqlite_query_only"] is True

        for path in cases:
            py_response = client.get(path)
            go_status, go_json = _read_json(base + path)
            assert go_status == py_response.status_code, path
            assert _normalize(go_json) == _normalize(py_response.get_json()), path
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
