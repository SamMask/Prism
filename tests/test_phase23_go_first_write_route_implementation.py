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


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-first-write-route-implementation.json"
SELECTION_PATH = ROOT / "docs" / "contracts" / "phase23-go-write-surface-selection.json"
GO_MAIN_PATH = GO_SHADOW_DIR / "main.go"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _read_json(url, *, data=None, method="GET"):
    body = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _copy_db(src, dst):
    shutil.copyfile(src, dst)
    return str(dst)


def _seed_tag_write_fixture(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('alpha-tag')")
        conn.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('beta-tag')")
        alpha_id = conn.execute("SELECT id FROM Tags WHERE name = 'alpha-tag'").fetchone()[0]
        beta_id = conn.execute("SELECT id FROM Tags WHERE name = 'beta-tag'").fetchone()[0]
        note_id = conn.execute("SELECT id FROM Notes ORDER BY id LIMIT 1").fetchone()[0]
        conn.execute(
            "INSERT OR IGNORE INTO Note_Tags (note_id, tag_id) VALUES (?, ?)",
            (note_id, alpha_id),
        )
        conn.commit()
        return {"alpha_id": alpha_id, "beta_id": beta_id, "note_id": note_id}
    finally:
        conn.close()


def _snapshot(db_path):
    conn = sqlite3.connect(db_path)
    try:
        tags = conn.execute("SELECT id, name FROM Tags ORDER BY id").fetchall()
        note_tags = conn.execute("SELECT note_id, tag_id FROM Note_Tags ORDER BY note_id, tag_id").fetchall()
        return {"tags": tags, "note_tags": note_tags}
    finally:
        conn.close()


def _start_go_candidate(go_bin, db_path, port, tmp_path):
    proc = subprocess.Popen(
        [
            go_bin,
            "run",
            ".",
            "--db",
            db_path,
            "--addr",
            f"127.0.0.1:{port}",
            "--data-dir",
            str(tmp_path),
            "--enable-tag-write",
        ],
        cwd=GO_SHADOW_DIR,
        env={**os.environ, "PRISM_GO_ENABLE_TAG_WRITE": "1"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            _read_json(base + "/api/test")
            return proc, base
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.25)
    output = proc.stdout.read() if proc.stdout else ""
    proc.terminate()
    pytest.fail(f"Go tag-write candidate did not start:\n{output}")


def _flask_client(db_path):
    from app import create_app

    app = create_app("testing")
    app.config.update(
        {
            "TESTING": True,
            "DATABASE": db_path,
            "WTF_CSRF_ENABLED": False,
            "PROPAGATE_EXCEPTIONS": True,
        }
    )
    ctx = app.app_context()
    ctx.push()
    return app.test_client(), ctx


def test_phase23_4_contract_records_local_copied_db_write_scope():
    contract = _contract()
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))

    assert contract["phase"] == "23.4"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-go-write-surface-selection.json"
    assert selection["selected_candidate"]["id"] == "tag_rename"
    assert contract["selected_route"] == "PUT /api/tags/<tag_id>"
    assert contract["runtime_change"] == "local_copied_db_only"
    assert contract["live_execution_authorized"] is False
    assert contract["production_db_write"] is False
    assert contract["caddy_or_service_change"] is False
    assert contract["pi_deploy"] is False


def test_go_tag_write_is_flag_gated_and_default_runtime_stays_read_only():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    contract = _contract()["implementation"]

    assert contract["enable_flag"] == "--enable-tag-write"
    assert contract["default_runtime_mode"]["sqlite_query_only"] is True
    assert contract["default_runtime_mode"]["api_surface"] == "get-read-only"
    assert contract["explicit_local_candidate_mode"]["sqlite_query_only"] is False
    assert "enableTagWrite" in main_go
    assert '"enable-tag-write"' in main_go
    assert '"PRISM_GO_ENABLE_TAG_WRITE"' in main_go
    assert "PRAGMA query_only = ON" in main_go
    assert "http.MethodPut" in main_go
    assert "http.MethodPost" not in main_go
    assert "http.MethodDelete" not in main_go
    assert "http.MethodPatch" not in main_go


@pytest.mark.parametrize(
    ("payload", "tag_key", "expected_status", "expected_body", "expect_change"),
    [
        ({"name": "  renamed-tag  "}, "alpha_id", 200, {"status": "success"}, True),
        ({}, "alpha_id", 400, {"status": "error", "message": "Tag name is required"}, False),
        ({"name": "   "}, "alpha_id", 400, {"status": "error", "message": "Tag name cannot be empty"}, False),
        ({"name": "new-name"}, "missing", 404, {"status": "error", "message": "Tag not found"}, False),
        ({"name": "beta-tag"}, "alpha_id", 409, {"status": "error", "message": "Tag name already exists"}, False),
    ],
)
def test_go_tag_rename_matches_python_response_and_db_state(
    temp_db, tmp_path, payload, tag_key, expected_status, expected_body, expect_change
):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; static contract checks still run.")

    py_db = _copy_db(temp_db, tmp_path / "python_tag_write_test.db")
    go_db = _copy_db(temp_db, tmp_path / "go_tag_write_test.db")
    py_ids = _seed_tag_write_fixture(py_db)
    go_ids = _seed_tag_write_fixture(go_db)
    assert py_ids == go_ids
    before = _snapshot(py_db)

    tag_id = 999999 if tag_key == "missing" else py_ids[tag_key]
    py_client, ctx = _flask_client(py_db)
    try:
        py_response = py_client.put(f"/api/tags/{tag_id}", json=payload)
        py_status = py_response.status_code
        py_json = py_response.get_json()
    finally:
        ctx.pop()

    port = _free_port()
    proc, base = _start_go_candidate(go_bin, go_db, port, tmp_path)
    try:
        health_status, health_json = _read_json(base + "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only+local-tag-write"
        assert health_json["runtime"]["sqlite_query_only"] is False

        go_status, go_json = _read_json(base + f"/api/tags/{tag_id}", data=payload, method="PUT")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert py_status == expected_status
    assert py_json == expected_body
    assert go_status == py_status
    assert go_json == py_json
    assert _snapshot(go_db) == _snapshot(py_db)

    if expect_change:
        tags = dict((tag_id, name) for tag_id, name in _snapshot(go_db)["tags"])
        assert tags[py_ids["alpha_id"]] == "renamed-tag"
        assert _snapshot(go_db)["note_tags"] == before["note_tags"]
    else:
        assert _snapshot(go_db) == before


def test_23_4_does_not_authorize_live_or_broader_write_scope():
    blocked = set(_contract()["not_authorized_by_23_4"])

    assert "Live Caddy route edit or reload" in blocked
    assert "systemd service change" in blocked
    assert "Production knowledge.db write" in blocked
    assert "Pi deployment" in blocked
    assert "Frontend default API target change" in blocked
    assert "Python route removal" in blocked
    assert "Go ownership of any route except local/copied-DB PUT /api/tags/<tag_id>" in blocked
    assert "Public exposure expansion" in blocked


def test_docs_record_23_4_completion_and_23_5_pending_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.4 First Go write route implementation gate — ✅ Completed (2026-06-05)" in todo
    assert "docs/contracts/phase23-go-first-write-route-implementation.json" in todo
    assert "23.5 Go DB-only write expansion gate — ✅ Completed (2026-06-05)" in todo
    assert "23.5 Next DB-only write implementation subgate — ✅ Completed (2026-06-05)" in todo
    assert "Phase 23.4 First Go write route implementation gate is complete" in architecture
    assert "Phase 23.5 Go DB-only write expansion gate is complete" in architecture
    assert "Phase 23.5-next.1 Second Go DB-only write implementation subgate is complete" in architecture
    assert "Phase 23.5-next.2-4 category update closure is complete" in architecture
    assert "Phase 23.6 File / attachment ownership gate is complete as a plan-only inventory and selection gate" in architecture
    assert "Next active Go gate is `23.6-next First Go file-read route implementation candidate`, pending explicit approval" in architecture
    assert "`23.4 First Go write route implementation gate is complete`" in go_report
    assert "`23.5 Go DB-only write expansion gate is complete`" in go_report
    assert "`23.5-next.1 Second Go DB-only write implementation subgate is complete`" in go_report
    assert "`23.5-next.2-4 Category update parity hardening, rollback lock, and boundary closure is complete`" in go_report
