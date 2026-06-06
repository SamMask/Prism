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
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-category-update-write-implementation.json"
CLOSURE_PATH = ROOT / "docs" / "contracts" / "phase23-go-category-update-closure.json"
SELECTION_PATH = ROOT / "docs" / "contracts" / "phase23-go-db-only-write-expansion-selection.json"
GO_MAIN_PATH = GO_SHADOW_DIR / "main.go"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _closure():
    return json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))


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


def _seed_category_fixture(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES ('alpha-category', 'A', 10, 0)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES ('beta-category', 'B', 20, 0)"
        )
        alpha_id = conn.execute("SELECT id FROM Categories WHERE name = 'alpha-category'").fetchone()[0]
        beta_id = conn.execute("SELECT id FROM Categories WHERE name = 'beta-category'").fetchone()[0]
        note_id = conn.execute("SELECT id FROM Notes ORDER BY id LIMIT 1").fetchone()[0]
        conn.execute("UPDATE Notes SET category_id = ? WHERE id = ?", (alpha_id, note_id))
        conn.commit()
        return {"alpha_id": alpha_id, "beta_id": beta_id, "note_id": note_id}
    finally:
        conn.close()


def _snapshot(db_path):
    conn = sqlite3.connect(db_path)
    try:
        categories = conn.execute(
            "SELECT id, name, icon, sort_order, is_default FROM Categories ORDER BY id"
        ).fetchall()
        notes = conn.execute("SELECT id, category_id FROM Notes ORDER BY id").fetchall()
        return {"categories": categories, "notes": notes}
    finally:
        conn.close()


def _start_go_candidate(go_bin, db_path, port, tmp_path, *, enable_category_write=True):
    args = [
        go_bin,
        "run",
        ".",
        "--db",
        db_path,
        "--addr",
        f"127.0.0.1:{port}",
        "--data-dir",
        str(tmp_path),
    ]
    env = {**os.environ}
    env.pop("PRISM_GO_ENABLE_CATEGORY_WRITE", None)
    if enable_category_write:
        args.append("--enable-category-write")
        env["PRISM_GO_ENABLE_CATEGORY_WRITE"] = "1"
    proc = subprocess.Popen(
        args,
        cwd=GO_SHADOW_DIR,
        env=env,
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
    pytest.fail(f"Go category-write candidate did not start:\n{output}")


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


def test_phase23_5_next_1_contract_records_local_copied_db_scope():
    contract = _contract()
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))

    assert contract["phase"] == "23.5-next.1"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-go-db-only-write-expansion-selection.json"
    assert selection["allowed_next_step"]["id"] == "23.5-next"
    assert contract["selected_route"] == "PUT /api/categories/<category_id>"
    assert contract["runtime_change"] == "local_copied_db_only"
    assert contract["live_execution_authorized"] is False
    assert contract["production_db_write"] is False
    assert contract["caddy_or_service_change"] is False
    assert contract["pi_deploy"] is False
    assert "trimmed empty category name returns 400 Category name cannot be empty" in contract["python_parity_contract"]["response_cases"]
    assert "duplicate, empty-name, and missing-body failures leave Categories unchanged" in contract["python_parity_contract"]["state_cases"]
    assert "trimmed empty category name returns 400" in contract["python_parity_contract"]["runtime_truth_note"]


def test_go_category_write_is_flag_gated_and_default_runtime_stays_read_only():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    implementation = _contract()["implementation"]

    assert implementation["enable_flag"] == "--enable-category-write"
    assert implementation["enable_env"] == "PRISM_GO_ENABLE_CATEGORY_WRITE=1"
    assert implementation["default_runtime_mode"]["sqlite_query_only"] is True
    assert implementation["default_runtime_mode"]["api_surface"] == "get-read-only"
    assert implementation["explicit_local_candidate_mode"]["sqlite_query_only"] is False
    assert "enableCategoryWrite" in main_go
    assert '"enable-category-write"' in main_go
    assert '"PRISM_GO_ENABLE_CATEGORY_WRITE"' in main_go
    assert "handleCategoryDetail" in main_go
    assert "updateCategory" in main_go
    assert "PRAGMA query_only = ON" in main_go
    assert "http.MethodPut" in main_go
    assert "Thumbnail write route is disabled" in main_go
    assert "enableNotesWrite" in main_go
    assert "Notes write route is disabled" in main_go
    assert "http.MethodPatch" not in main_go


@pytest.mark.parametrize(
    ("payload", "category_key", "expected_status", "expected_body", "expect_change"),
    [
        ({"name": "  renamed-category  "}, "alpha_id", 200, {"status": "success", "data": {"updated_notes_count": 0}}, True),
        ({"icon": "Z"}, "alpha_id", 200, {"status": "success", "data": {"updated_notes_count": 0}}, True),
        ({"sort_order": 77}, "alpha_id", 200, {"status": "success", "data": {"updated_notes_count": 0}}, True),
        ({"name": "combo-category", "icon": "C", "sort_order": 88}, "alpha_id", 200, {"status": "success", "data": {"updated_notes_count": 0}}, True),
        ({}, "alpha_id", 400, {"status": "error", "message": "Request body is required"}, False),
        ({"name": "missing-target"}, "missing", 404, {"status": "error", "message": "Category not found"}, False),
        ({"name": "beta-category"}, "alpha_id", 409, {"status": "error", "message": "Category name already exists"}, False),
        ({"name": "   "}, "alpha_id", 400, {"status": "error", "message": "Category name cannot be empty"}, False),
    ],
)
def test_go_category_update_matches_python_response_and_db_state(
    temp_db, tmp_path, payload, category_key, expected_status, expected_body, expect_change
):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; static contract checks still run.")

    py_db = _copy_db(temp_db, tmp_path / "python_category_write_test.db")
    go_db = _copy_db(temp_db, tmp_path / "go_category_write_test.db")
    py_ids = _seed_category_fixture(py_db)
    go_ids = _seed_category_fixture(go_db)
    assert py_ids == go_ids
    before = _snapshot(py_db)

    category_id = 999999 if category_key == "missing" else py_ids[category_key]
    py_client, ctx = _flask_client(py_db)
    try:
        py_response = py_client.put(f"/api/categories/{category_id}", json=payload)
        py_status = py_response.status_code
        py_json = py_response.get_json()
    finally:
        ctx.pop()

    port = _free_port()
    proc, base = _start_go_candidate(go_bin, go_db, port, tmp_path)
    try:
        health_status, health_json = _read_json(base + "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only+local-category-write"
        assert health_json["runtime"]["sqlite_query_only"] is False

        go_status, go_json = _read_json(base + f"/api/categories/{category_id}", data=payload, method="PUT")
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
        assert _snapshot(go_db)["notes"] == before["notes"]
    else:
        assert _snapshot(go_db) == before


def test_default_category_write_rejection_is_locked_by_go_unit_test():
    main_test = (GO_SHADOW_DIR / "main_test.go").read_text(encoding="utf-8")

    assert "TestCategoryWriteHandlerRejectsWhenFlagDisabled" in main_test
    assert "Category write route is disabled" in main_test
    assert "openDB(dbPath, false)" in main_test
    assert "http.StatusMethodNotAllowed" in main_test


def test_23_5_next_1_does_not_authorize_live_or_broader_write_scope():
    blocked = set(_contract()["not_authorized_by_23_5_next_1"])

    assert "Live category write routing gate" in blocked
    assert "Production knowledge.db write" in blocked
    assert "Pi deployment" in blocked
    assert "Caddy route edit or reload" in blocked
    assert "systemd service change" in blocked
    assert "Frontend default API target change" in blocked
    assert "Python route change" in blocked
    assert "Python route removal" in blocked
    assert "Schema migration" in blocked
    assert "Notes action Go ownership" in blocked
    assert "File upload or attachment ownership" in blocked


def test_23_5_next_2_4_closure_hardens_empty_name_and_locks_boundaries():
    closure = _closure()
    empty_name = closure["closure_decisions"]["empty_name_contract"]
    rollback = closure["closure_decisions"]["transaction_rollback_lock"]
    boundary = closure["closure_decisions"]["boundary_lock"]

    assert closure["phase"] == "23.5-next.2-4"
    assert closure["status"] == "completed"
    assert closure["explicit_user_approval"] is True
    assert closure["source_contract"] == "docs/contracts/phase23-go-category-update-write-implementation.json"
    assert closure["live_execution_authorized"] is False
    assert closure["production_db_write"] is False
    assert closure["caddy_or_service_change"] is False
    assert closure["pi_deploy"] is False
    assert empty_name["decision"] == "harden_python_and_go_to_return_400"
    assert empty_name["python_response"]["status_code"] == 400
    assert empty_name["python_response"]["body"]["message"] == "Category name cannot be empty"
    assert empty_name["go_response"] == empty_name["python_response"]
    assert "Trimmed empty category name leaves Categories unchanged" in rollback["failure_invariants"]
    assert "Notes.category_id assignments remain unchanged" in rollback["success_invariants"]
    assert boundary["default_go_runtime"] == "get-read-only with SQLite query_only = ON"
    assert "File upload or attachment ownership" in boundary["blocked_scope"]
    assert closure["allowed_next_step"]["id"] == "23.6"
    assert closure["allowed_next_step"]["requires_explicit_user_approval"] is True


def test_docs_record_23_5_next_1_completion_and_next_decision_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.5-next.1" in todo
    assert "✅ Completed (2026-06-05)" in todo
    assert "docs/contracts/phase23-go-category-update-write-implementation.json" in todo
    assert "23.5-next.2 Category update parity hardening and empty-name contract decision — ✅ Completed (2026-06-05)" in todo
    assert "docs/contracts/phase23-go-category-update-closure.json" in todo
    assert "Phase 23.5-next.1 Second Go DB-only write implementation subgate is complete" in architecture
    assert "Phase 23.5-next.2-4 category update closure is complete" in architecture
    assert "Phase 23.6 File / attachment ownership gate is complete as a plan-only inventory and selection gate" in architecture
    assert "Phase 23.6-next First Go file-read route implementation candidate is complete" in architecture
    assert "Phase 23.7 Migration / DB ownership decision gate is complete as plan-only" in architecture
    assert "Phase 23.9 Pi deployment rollout is complete" in architecture
    assert "Phase 23 Go runtime reduction track is closed with retained-Python normal path" in architecture
    assert "`23.5-next.1 Second Go DB-only write implementation subgate is complete`" in go_report
    assert "`23.5-next.2-4 Category update parity hardening, rollback lock, and boundary closure is complete`" in go_report
    assert "`23.6 File / attachment ownership gate` is complete as a plan-only inventory and selection gate" in go_report
    assert "`23.6-next First Go file-read route implementation candidate` is complete" in go_report
    assert "`23.7 Migration / DB ownership decision gate` is complete as plan-only" in go_report
    assert "`23.9 Pi deployment rollout` is complete" in go_report
    assert "Phase 23 closes with retained Python as the normal runtime path" in go_report
