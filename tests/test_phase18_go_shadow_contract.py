import json
import os
import shutil
import socket
import subprocess
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
    "/api/notes/1",
    "/api/notes?q=Welcome&page=1&per_page=20",
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
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_go_shadow_scaffold_is_read_only():
    main_go = (GO_SHADOW_DIR / "main.go").read_text(encoding="utf-8")

    assert (GO_SHADOW_DIR / "go.mod").exists()
    assert "PRAGMA query_only = ON" in main_go
    assert "refusing to open production-like database" in main_go
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

    port = _free_port()
    env = os.environ.copy()
    env["PRISM_GO_DB"] = temp_db
    env["PRISM_GO_ADDR"] = f"127.0.0.1:{port}"
    proc = subprocess.Popen(
        [go_bin, "run", ".", "--db", temp_db, "--addr", f"127.0.0.1:{port}"],
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

        for path in CASES:
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
