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

from tests.go_primary_parity_harness import RouteParityFixture, build_go_shadow_exe, run_python_go_fixture


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"
MANIFEST_PATH = ROOT / "docs" / "contracts" / "go-primary-route-ownership-manifest.json"
PARITY_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-parity-fixture-harness.json"
CONFIG_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-runtime-config-data-dir.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _route_keys_from_manifest():
    manifest = _load_json(MANIFEST_PATH)
    keys = set()
    for route in manifest["routes"]:
        for method in route["methods"]:
            keys.add((method, route["rule"], route["endpoint"]))
    return keys


def _flask_route_keys(monkeypatch, v2_mode):
    if v2_mode:
        monkeypatch.setenv("PRISM_V2", "true")
    else:
        monkeypatch.delenv("PRISM_V2", raising=False)

    from app import create_app

    app = create_app("testing")
    keys = set()
    for rule in app.url_map.iter_rules():
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            keys.add((method, rule.rule, rule.endpoint))
    return keys


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_json(url, timeout=30):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(0.25)
    raise AssertionError(f"{url} did not become ready: {last_error}")


def test_t004_route_manifest_covers_default_and_v2_flask_url_maps(monkeypatch):
    manifest_keys = _route_keys_from_manifest()

    for v2_mode in (False, True):
        actual = _flask_route_keys(monkeypatch, v2_mode)
        missing = sorted(actual - manifest_keys)
        assert missing == []


def test_t004_manifest_records_owner_handler_and_side_effect_shape():
    manifest = _load_json(MANIFEST_PATH)

    assert manifest["task_id"] == "T004"
    assert manifest["status"] == "completed"
    assert manifest["last_refreshed_task_id"] == "T051"
    assert manifest["production_runtime_owner"] == "go-primary"
    assert manifest["source_of_truth"] == "Flask app.url_map"

    for route in manifest["routes"]:
        assert route["rule"]
        assert route["endpoint"]
        assert route["methods"]
        assert route["python_handler"]
        assert route["production_owner"] != "python"
        assert route["go_primary_owner"]
        assert route["current_owner_note"]
        assert "db_side_effects" in route
        assert "file_side_effects" in route
        assert isinstance(route["db_side_effects"], list)
        assert isinstance(route["file_side_effects"], list)

    upload = next(
        route
        for route in manifest["routes"]
        if route["rule"] == "/api/upload" and route["methods"] == ["POST"]
    )
    assert "write static/uploads original and thumbnail files" in upload["file_side_effects"]

    migration = next(
        route for route in manifest["routes"] if route["rule"] == "/api/system/migration-status"
    )
    assert migration["production_owner"] == "go-primary"
    assert migration["go_primary_owner"] == "go-primary runtime route"

    read_routing = next(
        route for route in manifest["routes"] if route["rule"] == "/api/system/go-read-routing"
    )
    assert read_routing["production_owner"] == "legacy-python-source-only"
    assert "legacy Flask source" in read_routing["go_primary_owner"]


def test_t005_parity_harness_contract_exposes_status_json_db_and_file_diffs():
    contract = _load_json(PARITY_CONTRACT_PATH)
    harness_source = (ROOT / contract["harness_path"]).read_text(encoding="utf-8")

    assert contract["task_id"] == "T005"
    assert contract["status"] == "completed"
    assert contract["fixture_contract"]["declares"] == [
        "method",
        "path",
        "json_body",
        "headers",
        "db_tables",
        "file_roots",
        "normalize_json_keys",
    ]
    for diff_key in ("status_code", "json_body", "db_mutation", "file_mutation"):
        assert diff_key in contract["diff_format"]
        assert diff_key in harness_source

    assert "RouteParityFixture" in harness_source
    assert "observe_flask_fixture" in harness_source
    assert "observe_http_fixture" in harness_source
    assert "run_python_go_fixture" in harness_source


def test_t005_harness_runs_declared_fixture_against_python_and_go(client, app, temp_db, tmp_path, monkeypatch):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; harness shape tests still run.")

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(app, "root_path", str(data_dir))
    port = _free_port()
    exe_path = build_go_shadow_exe(go_bin, tmp_path)
    proc = subprocess.Popen(
        [
            str(exe_path),
            "--db",
            temp_db,
            "--addr",
            f"127.0.0.1:{port}",
            "--data-dir",
            str(data_dir),
        ],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        status, health = _wait_for_json(base + "/healthz")
        assert status == 200
        assert health["runtime"]["data_dir"] == str(data_dir)

        fixture = RouteParityFixture(
            id="api_test_read",
            method="GET",
            path="/api/test",
            db_tables=("Notes", "Categories", "Tags"),
            file_roots=("static/uploads",),
        )
        result = run_python_go_fixture(
            client,
            base,
            fixture,
            python_db_path=temp_db,
            go_db_path=temp_db,
            python_data_dir=str(data_dir),
            go_data_dir=str(data_dir),
        )
        assert result["ok"], result["diffs"]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_t006_runtime_config_contract_and_go_source_lock_external_data_dir():
    contract = _load_json(CONFIG_CONTRACT_PATH)
    main_go = (GO_SHADOW_DIR / "main.go").read_text(encoding="utf-8")
    go_tests = (GO_SHADOW_DIR / "main_test.go").read_text(encoding="utf-8")

    assert contract["task_id"] == "T006"
    assert contract["status"] == "completed"
    assert contract["data_dir"]["required"] is True
    assert contract["data_dir"]["rejects_unspecified"] is True
    assert contract["db_path"]["relative_paths_resolve_under_data_dir"] is True
    assert contract["db_path"]["relative_traversal_rejected"] is True
    assert contract["resolved_roots"] == {
        "db": "explicit --db / PRISM_GO_DB; relative paths resolve under data_dir",
        "uploads": "static/uploads",
        "attachments": "docs/attachments",
        "logs": "logs",
        "backups": "backups",
        "config": "config",
    }

    assert 'os.Getenv("PRISM_GO_DATA_DIR")' in main_go
    assert "data directory is required" in main_go
    assert "resolveDataRootPath" in main_go
    assert "ensureDataSubdir" in main_go
    assert "uploadsDir" in main_go
    assert "attachmentsDir" in main_go
    assert "backupsDir" in main_go
    assert "TestRuntimeConfigRequiresExplicitDataDir" in go_tests
    assert "TestRuntimeConfigResolvesRelativeDBInsideDataDirAndRejectsTraversal" in go_tests


def test_docs_mark_t004_t005_t006_done_and_record_boundaries():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")

    for task_id in ("T004", "T005", "T006"):
        row = next(line for line in todo.splitlines() if line.startswith(f"| {task_id} "))
        assert row.endswith("| Done |")

    assert "go-primary-route-ownership-manifest.json" in todo
    assert "go-primary-parity-fixture-harness.json" in todo
    assert "go-primary-runtime-config-data-dir.json" in todo
    assert "T004-T006 foundation gates are complete" in architecture
    assert "does not promote any route to live Go ownership" in architecture
