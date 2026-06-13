"""Pure-Go end-to-end acceptance net (T053 prerequisite, Gate item 1).

This is the verification net the deletion-boundary proof
(`docs/T053-source-deletion-boundary-inventory.md`) requires *before* the
retained-Python backend source closure can be removed.

Unlike the parity tests, this module uses **no Python backend as oracle**:
- It boots the Go runtime on a fresh **Go-created** DB (no `temp_db` fixture,
  no `migrations`, no `app.create_app`).
- It drives the full workflow over Go HTTP only, reusing the already
  stdlib-only smoke (`scripts/go_primary_full_workflow_smoke.py`).

Therefore it stays valid after T053 deletes `app.py` / `routes/` / `migrations/`.
A guard test below proves this module (and the reused smoke) imports no Flask
backend, so the acceptance net does not silently regrow a Python dependency.
"""

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
SCRIPTS_DIR = ROOT / "scripts"
SMOKE_PATH = SCRIPTS_DIR / "go_primary_full_workflow_smoke.py"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from go_primary_full_workflow_smoke import run_smoke  # noqa: E402  (path set above)


# Mirror the production launch surface (scripts/start_go_primary.ps1) so the
# acceptance net boots the exact runtime the Pi serves, not a reduced subset.
GO_PRODUCTION_FLAGS = (
    "--enable-tag-write",
    "--enable-category-write",
    "--enable-notes-write",
    "--enable-attachment-text-read",
    "--enable-attachment-raw-read",
    "--enable-attachment-write",
    "--enable-upload-write",
    "--enable-thumbnail-write",
    "--enable-upload-url-write",
    "--enable-upload-delete",
    "--enable-media-cleanup",
    "--enable-import-export",
    "--enable-server-system",
)

# A dev-named DB under the data dir: the runtime fresh-inits it. A production
# name like knowledge.db would be rejected by the default prod-DB guard.
DB_REL = "e2e/prism_e2e_acceptance.db"


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _request_json(base, path):
    request = urllib.request.Request(base.rstrip("/") + path, method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:
        import json

        return response.status, json.loads(response.read().decode("utf-8"))


def _wait_health(base, deadline_seconds=30):
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        try:
            return _request_json(base, "/healthz")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.25)
    return None


def _stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_pure_go_fresh_runtime_passes_full_workflow_without_python_backend(tmp_path):
    """Boot Go on a fresh Go-created DB and run the whole workflow over HTTP.

    No Flask client, no migrations import: this is the Python-independent
    acceptance gate that must pass before T053 removes the Python source.
    """
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; pure-Go acceptance net cannot run.")

    data_dir = tmp_path / "data"
    db_path = data_dir / "e2e" / "prism_e2e_acceptance.db"
    port = _free_port()
    exe_path = build_go_shadow_exe(go_bin, tmp_path)

    proc = subprocess.Popen(
        [
            str(exe_path),
            "--db",
            DB_REL,
            "--addr",
            f"127.0.0.1:{port}",
            "--data-dir",
            str(data_dir),
            *GO_PRODUCTION_FLAGS,
        ],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        health = _wait_health(base)
        if health is None:
            output = proc.stdout.read() if proc.stdout else ""
            pytest.fail(f"Go pure-Go acceptance runtime did not start:\n{output}")

        status, payload = health
        assert status == 200
        runtime = payload["runtime"]
        # The runtime built its own schema from scratch — no Python migration.
        assert runtime["schema_version"] == 16
        assert runtime["expected_schema_version"] == 16
        assert runtime["fresh_db_initialized"] is True

        # Full workflow over Go HTTP only (create/upload/search/export/import/
        # delete/orphan-cleanup/backup/migration-status).
        evidence = run_smoke(base, "pure-go-e2e")
        assert evidence["status"] == "passed", evidence

        # The Go-created DB is real, current, and survived the workflow.
        assert db_path.exists()
        with open(db_path, "rb") as handle:
            assert handle.read(16).startswith(b"SQLite format 3")
        conn = sqlite3.connect(db_path)
        try:
            version = conn.execute(
                "SELECT value FROM Schema_Meta WHERE key = 'schema_version'"
            ).fetchone()[0]
            assert version == "16"
        finally:
            conn.close()
    finally:
        _stop(proc)


def test_acceptance_net_has_no_python_backend_imports():
    """Guard: this net must remain valid after T053 deletes the Python source.

    If anyone reintroduces a Flask-backend import into the acceptance net or the
    reused smoke, this fails — keeping the gate genuinely Python-independent.
    """
    # Match real import statements only (start-of-line from/import), so prose in
    # docstrings that merely names the backend does not trip the guard. The
    # regex already covers `from app import create_app` via the `from app` head.
    forbidden = re.compile(
        r"^\s*(?:from|import)\s+(app|routes|migrations|services|config|db)\b",
        re.MULTILINE,
    )
    for source_path in (Path(__file__), SMOKE_PATH):
        text = source_path.read_text(encoding="utf-8")
        offenders = forbidden.findall(text)
        assert not offenders, f"{source_path.name} imports Python backend: {offenders}"
