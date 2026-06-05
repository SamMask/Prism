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
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-attachment-text-read-implementation.json"
SOURCE_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-file-attachment-ownership-gate.json"
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


def _read_json(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _copy_db(src, dst):
    shutil.copyfile(src, dst)
    return str(dst)


def _seed_attachment_fixture(db_path, data_root):
    attachment_dir = Path(data_root) / "docs" / "attachments"
    upload_dir = Path(data_root) / "static" / "uploads"
    attachment_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "keep.txt").write_text("uploads must not change", encoding="utf-8")

    (attachment_dir / "text-fixture.md").write_text("hello from copied attachment\n第二行", encoding="utf-8")
    (attachment_dir / "unsupported.html").write_text("unsupported body", encoding="utf-8")

    conn = sqlite3.connect(db_path)
    try:
        note_id = conn.execute("SELECT id FROM Notes ORDER BY id LIMIT 1").fetchone()[0]
        conn.execute(
            """
            INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted)
            VALUES (?, 'docs/attachments/text-fixture.md', 'md', 'Text Fixture', 32, 0)
            """,
            (note_id,),
        )
        text_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted)
            VALUES (?, 'docs/attachments/missing.md', 'md', 'Missing Fixture', 0, 0)
            """,
            (note_id,),
        )
        missing_file_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted)
            VALUES (?, '../outside.md', 'md', 'Unsafe Fixture', 0, 0)
            """,
            (note_id,),
        )
        unsafe_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted)
            VALUES (?, 'docs/attachments/unsupported.html', 'html', 'Unsupported Fixture', 16, 0)
            """,
            (note_id,),
        )
        unsupported_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        return {
            "text_id": text_id,
            "missing_file_id": missing_file_id,
            "unsafe_id": unsafe_id,
            "unsupported_id": unsupported_id,
        }
    finally:
        conn.close()


def _tree_bytes(root):
    root = Path(root)
    if not root.exists():
        return {}
    out = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        out[path.relative_to(root).as_posix()] = path.read_bytes()
    return out


def _start_go_candidate(go_bin, db_path, port, data_root, *, enable_attachment_text_read=True):
    args = [
        go_bin,
        "run",
        ".",
        "--db",
        db_path,
        "--addr",
        f"127.0.0.1:{port}",
        "--data-dir",
        str(data_root),
    ]
    env = {**os.environ}
    env.pop("PRISM_GO_ENABLE_ATTACHMENT_TEXT_READ", None)
    if enable_attachment_text_read:
        args.append("--enable-attachment-text-read")
        env["PRISM_GO_ENABLE_ATTACHMENT_TEXT_READ"] = "1"
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
    pytest.fail(f"Go attachment-text candidate did not start:\n{output}")


def _flask_client(db_path, data_root):
    from app import create_app

    app = create_app("testing")
    app.root_path = str(data_root)
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


def test_phase23_6_next_contract_records_local_text_json_scope():
    contract = _contract()
    source = json.loads(SOURCE_CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["phase"] == "23.6-next"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-go-file-attachment-ownership-gate.json"
    assert source["allowed_next_step"]["id"] == "23.6-next"
    assert contract["selected_route"] == "GET /api/attachments/<attachment_id>"
    assert contract["selected_branch"] == "text JSON only; raw=true remains Python-owned"
    assert contract["runtime_change"] == "local_copied_db_and_copied_files_only"
    assert contract["live_execution_authorized"] is False
    assert contract["production_db_write"] is False
    assert contract["production_filesystem_mutation"] is False
    assert contract["filesystem_write_authorized"] is False
    assert contract["filesystem_delete_authorized"] is False
    assert contract["caddy_or_service_change"] is False
    assert contract["pi_deploy"] is False


def test_go_attachment_text_read_is_flag_gated_and_keeps_query_only():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    implementation = _contract()["implementation"]

    assert implementation["enable_flag"] == "--enable-attachment-text-read"
    assert implementation["enable_env"] == "PRISM_GO_ENABLE_ATTACHMENT_TEXT_READ=1"
    assert implementation["default_runtime_mode"]["sqlite_query_only"] is True
    assert implementation["default_runtime_mode"]["api_surface"] == "get-read-only"
    assert implementation["explicit_local_candidate_mode"]["sqlite_query_only"] is True
    assert implementation["explicit_local_candidate_mode"]["api_surface"] == "get-read-only+local-attachment-text-read"
    assert "enableAttachmentTextRead" in main_go
    assert '"enable-attachment-text-read"' in main_go
    assert '"PRISM_GO_ENABLE_ATTACHMENT_TEXT_READ"' in main_go
    assert "handleAttachmentDetail" in main_go
    assert "readAttachmentText" in main_go
    assert "Raw attachment responses remain Python-owned" in main_go
    assert "PRAGMA query_only = ON" in main_go
    assert "http.MethodPost" not in main_go
    assert "http.MethodDelete" not in main_go
    assert "http.MethodPatch" not in main_go


def test_go_attachment_text_read_matches_python_success_and_missing_id(temp_db, tmp_path):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; static contract checks still run.")

    py_root = tmp_path / "python_root"
    go_root = tmp_path / "go_root"
    py_db = _copy_db(temp_db, tmp_path / "python_attachment_text_test.db")
    go_db = _copy_db(temp_db, tmp_path / "go_attachment_text_test.db")
    py_ids = _seed_attachment_fixture(py_db, py_root)
    go_ids = _seed_attachment_fixture(go_db, go_root)
    assert py_ids == go_ids

    py_client, ctx = _flask_client(py_db, py_root)
    try:
        py_success = py_client.get(f"/api/attachments/{py_ids['text_id']}")
        py_missing_id = py_client.get("/api/attachments/999999")
    finally:
        ctx.pop()

    port = _free_port()
    proc, base = _start_go_candidate(go_bin, go_db, port, go_root)
    try:
        health_status, health_json = _read_json(base + "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only+local-attachment-text-read"
        assert health_json["runtime"]["sqlite_query_only"] is True

        db_before = Path(go_db).read_bytes()
        attachments_before = _tree_bytes(go_root / "docs" / "attachments")
        uploads_before = _tree_bytes(go_root / "static" / "uploads")

        go_success = _read_json(base + f"/api/attachments/{go_ids['text_id']}")
        go_missing_id = _read_json(base + "/api/attachments/999999")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert go_success == (py_success.status_code, py_success.get_json())
    assert go_missing_id == (py_missing_id.status_code, py_missing_id.get_json())
    assert Path(go_db).read_bytes() == db_before
    assert _tree_bytes(go_root / "docs" / "attachments") == attachments_before
    assert _tree_bytes(go_root / "static" / "uploads") == uploads_before


@pytest.mark.parametrize(
    ("fixture_key", "expected_status", "expected_message"),
    [
        ("missing_file_id", 404, "File not found on disk"),
        ("unsafe_id", 404, "File not found on disk"),
        ("unsupported_id", 404, "File not found on disk"),
    ],
)
def test_go_attachment_text_read_failure_cases_do_not_mutate_files_or_db(
    temp_db, tmp_path, fixture_key, expected_status, expected_message
):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; static contract checks still run.")

    go_root = tmp_path / "go_root"
    go_db = _copy_db(temp_db, tmp_path / "go_attachment_text_failure_test.db")
    ids = _seed_attachment_fixture(go_db, go_root)

    port = _free_port()
    proc, base = _start_go_candidate(go_bin, go_db, port, go_root)
    try:
        _read_json(base + "/healthz")
        db_before = Path(go_db).read_bytes()
        attachments_before = _tree_bytes(go_root / "docs" / "attachments")
        uploads_before = _tree_bytes(go_root / "static" / "uploads")
        status, payload = _read_json(base + f"/api/attachments/{ids[fixture_key]}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert status == expected_status
    assert payload == {"status": "error", "message": expected_message}
    assert Path(go_db).read_bytes() == db_before
    assert _tree_bytes(go_root / "docs" / "attachments") == attachments_before
    assert _tree_bytes(go_root / "static" / "uploads") == uploads_before


def test_go_attachment_text_read_blocks_raw_branch_and_default_disabled_route(temp_db, tmp_path):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; static contract checks still run.")

    go_root = tmp_path / "go_root"
    go_db = _copy_db(temp_db, tmp_path / "go_attachment_text_disabled_test.db")
    ids = _seed_attachment_fixture(go_db, go_root)

    enabled_port = _free_port()
    enabled_proc, enabled_base = _start_go_candidate(go_bin, go_db, enabled_port, go_root)
    try:
        raw_status, raw_payload = _read_json(enabled_base + f"/api/attachments/{ids['text_id']}?raw=true")
    finally:
        enabled_proc.terminate()
        try:
            enabled_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            enabled_proc.kill()

    disabled_port = _free_port()
    disabled_proc, disabled_base = _start_go_candidate(
        go_bin, go_db, disabled_port, go_root, enable_attachment_text_read=False
    )
    try:
        disabled_status, disabled_payload = _read_json(disabled_base + f"/api/attachments/{ids['text_id']}")
    finally:
        disabled_proc.terminate()
        try:
            disabled_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            disabled_proc.kill()

    assert raw_status == 405
    assert raw_payload == {"status": "error", "message": "Raw attachment responses remain Python-owned"}
    assert disabled_status == 405
    assert disabled_payload == {"status": "error", "message": "Attachment text read route is disabled"}


def test_23_6_next_does_not_authorize_live_or_broader_file_scope():
    blocked = set(_contract()["not_authorized_by_23_6_next"])

    assert "raw=true Go ownership" in blocked
    assert "binary or send_file response Go ownership" in blocked
    assert "attachment upload Go ownership" in blocked
    assert "attachment delete Go ownership" in blocked
    assert "cleanup route Go ownership" in blocked
    assert "import or export Go ownership" in blocked
    assert "server backup or log route Go ownership" in blocked
    assert "live route expansion" in blocked
    assert "Production knowledge.db write" in blocked
    assert "Production attachment or upload filesystem mutation" in blocked
    assert "Pi deployment" in blocked
    assert "Caddy route edit or reload" in blocked
    assert "Python route removal" in blocked
    assert "Schema migration" in blocked
    assert "Public exposure expansion" in blocked


def test_docs_record_23_6_next_completion_and_23_7_next_gate():
    contract = _contract()
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert contract["allowed_next_step"]["id"] == "23.7"
    assert contract["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "23.6-next First Go file-read route implementation candidate — ✅ Completed (2026-06-06)" in todo
    assert "docs/contracts/phase23-go-attachment-text-read-implementation.json" in todo
    assert "23.7 Migration / DB ownership decision gate — ✅ Completed (2026-06-06)" in todo
    assert "23.8 Local packaging execution track — Active" in todo
    assert "Phase 23.6-next First Go file-read route implementation candidate is complete" in architecture
    assert "Phase 23.7 Migration / DB ownership decision gate is complete as plan-only" in architecture
    assert "Next active Go gate is `23.8.2 Local smoke artifact`" in architecture
    assert "`23.6-next First Go file-read route implementation candidate` is complete" in go_report
    assert "`23.7 Migration / DB ownership decision gate` is complete as plan-only" in go_report
    assert "`23.8.2 Local smoke artifact` is the next recommended packaging step" in go_report
