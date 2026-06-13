# -*- coding: utf-8 -*-
"""Prism test configuration (conftest.py).

Post-T053: the Python Flask backend is gone, so the shared `temp_db` fixture no
longer runs `migrations.run_migrations` against a hand-rolled base schema. It now
seeds from a **real Go-created fresh DB** (the production schema path) and hands
out a per-test copy. The retired Flask fixtures (`client`, `app`, `app_with_db`)
were removed with their last consumers; the remaining GO-ONLY runtime tests use
`temp_db` purely as a current-schema seed DB to copy and drive the Go runtime.
"""

import os
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

import pytest

from tests.go_primary_parity_harness import build_go_shadow_exe


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_health(base, timeout=30):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=3) as response:
                return response.status
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            time.sleep(0.25)
    raise AssertionError(f"{base}/healthz did not become ready: {last_error}")


@pytest.fixture(scope="session")
def _go_seed_template(tmp_path_factory):
    """Fresh Go-created DB used as the seed template for `temp_db`.

    Built once per session: boot the Go runtime on an empty data dir so it
    fresh-inits the current schema (categories + welcome note id=1), then stop
    and checkpoint so the file is self-contained for copying.
    """
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; Go-seeded temp_db unavailable.")

    build_dir = tmp_path_factory.mktemp("seed_build")
    exe_path = build_go_shadow_exe(go_bin, build_dir)
    data_dir = tmp_path_factory.mktemp("seed_data") / "data"
    template_db = data_dir / "seed" / "template.db"
    port = _free_port()
    proc = subprocess.Popen(
        [
            str(exe_path),
            "--db", "seed/template.db",
            "--addr", f"127.0.0.1:{port}",
            "--data-dir", str(data_dir),
        ],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        try:
            assert _wait_health(f"http://127.0.0.1:{port}") == 200
        except Exception as exc:
            proc.terminate()
            output, _ = proc.communicate(timeout=5)
            raise AssertionError(output) from exc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    with sqlite3.connect(template_db) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return template_db


@pytest.fixture(scope="function")
def temp_db(_go_seed_template):
    """Per-test copy of the Go-created seed DB (current schema, isolated)."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    shutil.copy(_go_seed_template, db_path)
    yield db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass
