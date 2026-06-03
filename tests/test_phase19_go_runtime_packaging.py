import os
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for(url, timeout=10):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return response.status, response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - diagnostic payload
            last_error = exc
            time.sleep(0.2)
    raise AssertionError(f"{url} did not become ready: {last_error}")


def test_phase19_go_runtime_build_paths_and_windows_smoke(temp_db, tmp_path):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; build path proof cannot run.")

    exe_name = "prism-go-runtime.exe" if os.name == "nt" else "prism-go-runtime"
    windows_bin = tmp_path / exe_name
    subprocess.run(
        [go_bin, "build", "-o", str(windows_bin), "."],
        cwd=GO_SHADOW_DIR,
        check=True,
    )
    assert windows_bin.exists()

    port = _free_port()
    proc = subprocess.Popen(
        [
            str(windows_bin),
            "--db",
            temp_db,
            "--addr",
            f"127.0.0.1:{port}",
            "--data-dir",
            str(tmp_path / "data"),
        ],
        cwd=GO_SHADOW_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        status, body = _wait_for(f"http://127.0.0.1:{port}/healthz")
        assert status == 200
        assert '"go-runtime-proof"' in body

        status, html = _wait_for(f"http://127.0.0.1:{port}/")
        assert status == 200
        assert "<html" in html.lower()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    pi_bin = tmp_path / "prism-go-runtime-linux-arm64"
    env = os.environ.copy()
    env["GOOS"] = "linux"
    env["GOARCH"] = "arm64"
    env["CGO_ENABLED"] = "0"
    subprocess.run(
        [go_bin, "build", "-o", str(pi_bin), "."],
        cwd=GO_SHADOW_DIR,
        env=env,
        check=True,
    )
    assert pi_bin.exists()
    assert pi_bin.stat().st_size > 0
