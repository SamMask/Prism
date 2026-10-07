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

from tests.go_primary_parity_harness import build_go_shadow_exe
from tests.go_source_assertions import read_go_package_source


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"
TODO_PATH = ROOT / "docs" / "development-history" / "go-primary-runtime-completion-20260617.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
ARCHITECTURE_HISTORY_PATH = ROOT / "docs" / "development-history" / "architecture-go-migration-history-20261006.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
GO_README_PATH = ROOT / "go-shadow" / "README.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"
ROUTE_MANIFEST_PATH = ROOT / "docs" / "contracts" / "go-primary-route-ownership-manifest.json"
CONTRACTS = {
    "T032": ROOT / "docs" / "contracts" / "go-primary-server-status-parity.json",
    "T033": ROOT / "docs" / "contracts" / "go-primary-backup-management-parity.json",
    "T034": ROOT / "docs" / "contracts" / "go-primary-port-config-service-parity.json",
    "T035": ROOT / "docs" / "contracts" / "go-primary-prompt-wizard-options-parity.json",
}


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
    pytest.fail(f"Go T032-T035 candidate did not start:\n{output}")


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


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_backup(backup_dir, filename, content=b"backup", mtime=1):
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / filename
    path.write_bytes(content)
    os.utime(path, (mtime, mtime))
    return path


def test_t032_server_status_gate_and_system_shapes(temp_db, tmp_path):
    disabled_db = _copy_db(temp_db, tmp_path / "go_t032_disabled.db")
    disabled_data = tmp_path / "disabled_data"
    proc, base = _start_go(disabled_db, disabled_data, tmp_path)
    try:
        status, payload, _ = _request_json(base, "/api/server/version")
        assert status == 405
        assert payload["message"] == "Server/system route is disabled"
    finally:
        _stop(proc)

    go_db = _copy_db(temp_db, tmp_path / "go_t032.db")
    go_data = tmp_path / "go_data"
    go_data.mkdir()
    (go_data / "app.log").write_text(
        "[INFO] boot\n[WARNING] careful\n[ERROR] failed once\n",
        encoding="utf-8",
    )
    conn = sqlite3.connect(go_db)
    try:
        conn.execute(
            "INSERT INTO Note_History (note_id, content, diff_summary) VALUES (1, 'old', 'seed')"
        )
        conn.commit()
    finally:
        conn.close()

    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-server-system")
    try:
        status, payload, _ = _request_json(base, "/healthz")
        assert status == 200
        assert payload["runtime"]["api_surface"] == "get-read-only+local-server-system"
        assert payload["runtime"]["sqlite_query_only"] is False

        status, payload, _ = _request_json(base, "/api/server/version")
        assert status == 200
        assert payload["data"]["version"] == "2.7.0"
        assert payload["data"]["go_runtime"]["api_surface"] == "get-read-only+local-server-system"

        status, payload, _ = _request_json(base, "/api/system/stats")
        assert status == 200
        assert payload["data"]["database"]["notes_count"] >= 1
        assert payload["data"]["database"]["history_count"] == 1
        assert "uploads" in payload["data"]

        status, payload, _ = _request_json(base, "/api/server/hardware")
        assert status == 200
        assert {"memory", "disk", "database", "platform", "service_management"} <= set(
            payload["data"]
        )
        assert payload["data"]["service_management"]["available"] is True

        status, payload, _ = _request_json(base, "/api/server/logs?lines=2&level=ERROR")
        assert status == 200
        assert payload["data"]["lines"] == ["[ERROR] failed once"]
        assert payload["data"]["total_lines"] == 3

        status, payload, _ = _request_json(base, "/api/system/check-consistency")
        assert status == 200
        assert payload["data"]["health"] == "healthy"

        status, payload, _ = _request_json(base, "/api/system/clear-history", method="POST")
        assert status == 200
        assert payload["data"]["deleted_count"] == 1
    finally:
        _stop(proc)


def test_data_consistency_reports_foreign_key_violations_by_table(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_consistency_orphans.db")
    go_data = tmp_path / "go_consistency_data"
    conn = sqlite3.connect(go_db)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        orphan_note_id = 999_999
        conn.execute(
            "INSERT INTO Note_Attachments (note_id, file_path) VALUES (?, ?)",
            (orphan_note_id, "docs/attachments/orphan.md"),
        )
        conn.execute(
            "INSERT INTO Note_History (note_id, content, diff_summary) VALUES (?, ?, ?)",
            (orphan_note_id, "orphan history", "fixture"),
        )
        conn.execute(
            "INSERT INTO Source_Urls (note_id, url) VALUES (?, ?)",
            (orphan_note_id, "https://example.invalid/orphan"),
        )
        conn.commit()
    finally:
        conn.close()

    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-server-system")
    try:
        status, payload, _ = _request_json(base, "/api/system/check-consistency")
        assert status == 200
        assert payload["data"]["fk_enabled"] is True
        assert payload["data"]["foreign_key_violations_total"] == 3
        assert payload["data"]["foreign_key_violations_by_table"] == {
            "Note_Attachments": 1,
            "Note_History": 1,
            "Source_Urls": 1,
        }
        assert payload["data"]["health"] == "critical"
    finally:
        _stop(proc)


def test_t033_backup_list_download_rotate_delete_and_path_safety(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t033.db")
    go_data = tmp_path / "go_data"
    backup_dir = go_data / "backups"
    oldest = _write_backup(backup_dir, "prism_backup_20260601_120000.db", mtime=1)
    _write_backup(backup_dir, "prism_backup_20260602_120000.db", mtime=2)
    _write_backup(backup_dir, "prism_backup_20260603_120000.db", mtime=3)

    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-server-system")
    try:
        status, payload, _ = _request_json(base, "/api/server/backup/list")
        assert status == 200
        assert payload["data"]["count"] == 3

        status, headers, body = _request_bytes(base, "/api/server/backup/download")
        assert status == 200
        assert body.startswith(b"SQLite format 3")
        assert "application/x-sqlite3" in headers["Content-Type"]
        assert oldest.exists()
        assert len(list(backup_dir.glob("prism_backup_*.db"))) == 3

        status, payload, _ = _request_json(
            base,
            "/api/server/backup/rotate",
            method="POST",
            data={"keep": 2},
        )
        assert status == 200
        assert len(payload["data"]["kept_backups"]) == 2
        assert len(list(backup_dir.glob("prism_backup_*.db"))) == 2

        filename = payload["data"]["kept_backups"][0]["filename"]
        status, payload, _ = _request_json(
            base,
            f"/api/server/backup/{filename}",
            method="DELETE",
        )
        assert status == 200
        assert payload["data"]["deleted"] == filename
        assert not (backup_dir / filename).exists()

        status, payload, _ = _request_json(
            base,
            "/api/server/backup/manual.db",
            method="DELETE",
        )
        assert status == 400
        assert payload["message"] == "無效的備份檔名"
    finally:
        _stop(proc)


def test_t034_t035_port_startup_prompt_and_wizard_options(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t034_t035.db")
    go_data = tmp_path / "go_data"
    _write_json(
        go_data / "config" / "prompt_options.json",
        {
            "version": "1.0",
            "lastUpdated": "2026-01-01",
            "categories": {"style": {"label": "Style", "options": ["A"]}},
            "quickTemplates": [],
        },
    )
    _write_json(
        go_data / "config" / "wizard_options.json",
        {
            "version": "1.0",
            "lastUpdated": "2026-01-01",
            "dimensions": {"subject": {"label": "Subject", "options": ["first"]}},
        },
    )

    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-server-system")
    try:
        # PRISM-OPT-42 (2026-10-07): port-config and startup-preference were removed.
        # Even with --enable-server-system they fall through to the /api/ JSON 404
        # and no longer write marker files into the data dir. POSTs carry no body here:
        # the 404 fallback does not read request bodies, and on Windows an unread body can
        # reset the socket before the client reads the reply. The Go test
        # TestRemovedOPT42RoutesReturnAPINotFound covers POSTs with JSON bodies.
        for method, path in (
            ("GET", "/api/system/port-config"),
            ("POST", "/api/system/port-config"),
            ("GET", "/api/system/startup-preference"),
            ("POST", "/api/system/startup-preference"),
        ):
            status, payload, _ = _request_json(base, path, method=method)
            assert status == 404, (method, path, status, payload)
            assert payload["message"] == "API route not found"
        for marker in (".port_config", ".auto_open_yes", ".auto_open_no"):
            assert not (go_data / marker).exists()

        status, payload, _ = _request_json(base, "/api/prompt-options")
        assert status == 200
        assert payload["data"]["categories"]["style"]["options"] == ["A"]

        status, payload, _ = _request_json(
            base,
            "/api/prompt-options/category/style",
            method="POST",
            data={"value": "B"},
        )
        assert status == 201
        assert payload["data"]["index"] == 1

        status, payload, _ = _request_json(
            base,
            "/api/prompt-options/category/style/1",
            method="PUT",
            data={"value": "C"},
        )
        assert status == 200
        assert payload["data"]["option"] == "C"

        status, payload, _ = _request_json(
            base,
            "/api/prompt-options/template",
            method="POST",
            data={"id": "mine", "name": "Mine", "preset": {"style": "C"}},
        )
        assert status == 201
        assert payload["data"]["template"]["id"] == "mine"

        status, payload, _ = _request_json(
            base,
            "/api/prompt-options/template/mine",
            method="DELETE",
        )
        assert status == 200
        assert payload["data"]["deleted"]["id"] == "mine"

        status, payload, _ = _request_json(
            base,
            "/api/wizard-options/dimension/subject",
            method="POST",
            data={"value": "second"},
        )
        assert status == 201
        assert payload["data"]["option"] == "second"

        status, payload, _ = _request_json(
            base,
            "/api/wizard-options/dimension/subject/0",
            method="DELETE",
        )
        assert status == 200
        assert payload["data"]["deleted"] == "first"
    finally:
        _stop(proc)


def test_server_restart_really_exits_for_supervisor(temp_db, tmp_path, monkeypatch):
    # PRISM-OPT-36: under a supervisor (systemd sets INVOCATION_ID; tests use
    # PRISM_GO_SUPERVISED) the restart endpoint drains and exits with code 42 so
    # the supervisor relaunches Prism. It must no longer be a fake acknowledgement.
    monkeypatch.setenv("PRISM_GO_SUPERVISED", "1")
    go_db = _copy_db(temp_db, tmp_path / "go_restart.db")
    go_data = tmp_path / "go_restart_data"
    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-server-system")
    try:
        status, payload, _ = _request_json(base, "/api/server/restart", method="POST")
        assert status == 200
        assert payload["message"] == "restarting"
        assert payload["data"]["restarting"] is True
        assert payload["data"]["supervised"] is True
        assert payload["data"]["service_management"]["available"] is True
        assert proc.wait(timeout=15) == 42
    finally:
        _stop(proc)


def test_t032_t035_docs_and_contracts_are_updated():
    main_go = read_go_package_source(GO_SHADOW_DIR)
    assert "enable-server-system" in main_go
    assert "PRISM_GO_ENABLE_SERVER_SYSTEM" in main_go
    assert "local-server-system" in main_go

    todo = TODO_PATH.read_text(encoding="utf-8")
    for task_id in ("T032", "T033", "T034", "T035"):
        row = next(line for line in todo.splitlines() if line.startswith(f"| {task_id} |"))
        assert row.endswith("| Done |")

    for path in (ARCHITECTURE_HISTORY_PATH, GO_README_PATH, GO_REPORT_PATH):
        text = path.read_text(encoding="utf-8")
        assert "T032-T035" in text
        assert "local/copied" in text
        assert "production" in text.lower() or "正式" in text
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    assert "Migration v17" in schema
    assert "Go runtime 為唯一 migration owner" in schema

    manifest = json.loads(ROUTE_MANIFEST_PATH.read_text(encoding="utf-8"))
    server_system_routes = {
        "/api/system/stats",
        "/api/system/vacuum",
        "/api/system/clear-history",
        "/api/system/wal-checkpoint",
        "/api/system/check-consistency",
        "/api/server/hardware",
        "/api/server/logs",
        "/api/server/restart",
        "/api/server/backup/download",
        "/api/server/backup/rotate",
        "/api/server/backup/list",
        "/api/server/backup/<path:filename>",
        "/api/server/version",
        "/api/prompt-options",
        "/api/prompt-options/category/<category_key>",
        "/api/prompt-options/category/<category_key>/<int:index>",
        "/api/prompt-options/template",
        "/api/prompt-options/template/<template_id>",
        "/api/wizard-options",
        "/api/wizard-options/dimension/<dimension_key>",
        "/api/wizard-options/dimension/<dimension_key>/<int:index>",
    }
    candidates = {
        route["rule"]: route.get("go_candidate")
        for route in manifest["routes"]
        if route["rule"] in server_system_routes
    }
    assert set(candidates) == server_system_routes
    assert all("local copied" in value for value in candidates.values())
    removed_routes = [
        route
        for route in manifest["routes"]
        if route["rule"] in {"/api/system/port-config", "/api/system/startup-preference"}
    ]
    assert len(removed_routes) == 4
    assert all(route["production_owner"] == "removed-in-prism-opt-42" for route in removed_routes)
    assert '"/api/system/port-config"' not in main_go
    assert '"/api/system/startup-preference"' not in main_go

    for task_id, path in CONTRACTS.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["task_id"] == task_id
        assert payload["status"] == "completed"
        assert "production" in json.dumps(payload, ensure_ascii=False).lower()
    t034 = json.loads(CONTRACTS["T034"].read_text(encoding="utf-8"))
    assert "PRISM-OPT-42" in t034["removed"]
