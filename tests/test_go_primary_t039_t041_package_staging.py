import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = {
    "T039": ROOT / "docs" / "contracts" / "go-primary-windows-package-smoke.json",
    "T040": ROOT / "docs" / "contracts" / "go-primary-linux-arm64-package-smoke.json",
    "T041": ROOT / "docs" / "contracts" / "go-primary-pi-staging-unit.json",
}
FULL_WORKFLOW_SCRIPT = ROOT / "scripts" / "go_primary_full_workflow_smoke.py"
WINDOWS_PACKAGE_SCRIPT = ROOT / "scripts" / "smoke_go_primary_package.ps1"
PI_STAGING_SCRIPT = ROOT / "scripts" / "stage_go_primary_pi.ps1"
BUILD_SCRIPT = ROOT / "scripts" / "build_go_runtime.ps1"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
DEPLOY_PI_PATH = ROOT / "DEPLOY-PI.md"
GO_README_PATH = ROOT / "go-shadow" / "README.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"


def _contract(task_id):
    return json.loads(CONTRACTS[task_id].read_text(encoding="utf-8"))


def test_t039_t040_t041_contracts_record_package_and_staging_boundaries():
    t039 = _contract("T039")
    t040 = _contract("T040")
    t041 = _contract("T041")

    assert t039["status"] == "completed_package_candidate"
    assert t039["artifacts"] == {
        "windows": "build/go-runtime/prism-go-runtime.exe",
        "linux_arm64_presence_check": "build/go-runtime/prism-go-runtime-linux-arm64",
    }
    assert t039["runtime_dependency_boundary"]["python_venv_required_by_artifact"] is False
    assert t039["runtime_dependency_boundary"]["flask_required_by_artifact"] is False
    assert t039["runtime_dependency_boundary"]["pyinstaller_required_by_artifact"] is False
    assert t039["data_rule"]["db_source"].startswith("fresh Go-created DB")
    assert t039["data_rule"]["production_db_read"] is False

    assert t040["status"] == "completed_pi_staging_candidate"
    assert t040["artifact"] == "build/go-runtime/prism-go-runtime-linux-arm64"
    assert t040["execution_target"]["host_alias"] == "PI5Mask24"
    assert t040["execution_target"]["service"] == "prism-go-primary-staging.service"
    assert t040["runtime_dependency_boundary"]["python_venv_required_by_artifact"] is False
    assert t040["data_rule"]["production_db_mutated"] is False
    assert t040["data_rule"]["caddy_changed"] is False

    assert t041["status"] == "completed_staging_candidate"
    assert t041["staging_unit"]["service"] == "prism-go-primary-staging.service"
    assert t041["staging_unit"]["addr"] == "127.0.0.1:5003"
    assert t041["live_safety_guards"]["live_db_sha256_before_after_required"] is True
    assert t041["live_safety_guards"]["caddyfile_sha256_before_after_required"] is True
    assert t041["live_safety_guards"]["live_caddy_default_changed"] is False
    assert t041["next_recommended_task"]["id"] == "T042"


def test_full_workflow_smoke_harness_is_http_only_and_covers_primary_package_surface():
    script = FULL_WORKFLOW_SCRIPT.read_text(encoding="utf-8")

    assert "from app import" not in script
    assert "import flask" not in script.lower()
    assert "pyinstaller" not in script.lower()
    assert "urllib.request" in script
    for endpoint in [
        "/healthz",
        "/api/notes",
        "/api/upload",
        "/api/export/json",
        "/api/import/json",
        "/api/cleanup/orphan-images",
        "/api/server/backup/download",
        "/api/system/migration-status",
    ]:
        assert endpoint in script
    for marker in [
        "local-notes-write",
        "local-upload-write",
        "local-media-cleanup",
        "local-import-export",
        "local-server-system",
    ]:
        assert marker in script


def test_windows_package_script_uses_fresh_go_db_and_no_python_runtime_env():
    script = WINDOWS_PACKAGE_SCRIPT.read_text(encoding="utf-8")
    build_script = BUILD_SCRIPT.read_text(encoding="utf-8")

    assert "prism_windows_package_smoke_dev.db" in script
    assert "fresh Go-created DB under package smoke data dir" in script
    assert "Refusing to clean package smoke path outside repo build/" in script
    assert "go_primary_full_workflow_smoke.py" in script
    assert "VIRTUAL_ENV" in script and "PYTHONHOME" in script and "PYTHONPATH" in script
    assert "FLASK_APP" in script
    assert "knowledge.db" not in script
    assert "pyinstaller_required_by_artifact = $false" in script
    assert "pyinstaller " not in script.lower()
    assert "venv" not in build_script.lower()
    assert "python" not in build_script.lower()
    assert "pyinstaller" not in build_script.lower()
    assert 'GOOS = "linux"' in build_script
    assert 'GOARCH = "arm64"' in build_script
    assert 'CGO_ENABLED = "0"' in build_script


def test_pi_staging_script_writes_only_staging_unit_and_hash_guards_live_assets():
    script = PI_STAGING_SCRIPT.read_text(encoding="utf-8")

    assert 'HostAlias = "PI5Mask24"' in script
    assert 'RemoteRoot = "/home/mask070924/prism"' in script
    assert 'StageName = "go-primary-staging"' in script
    assert "prism-go-primary-staging.service" in script
    assert "knowledge_t041_staging.db" in script
    assert "--addr 127.0.0.1:$PORT" in script
    assert "live_hash_before" in script and "live_hash_after" in script
    assert "caddy_hash_before" in script and "caddy_hash_after" in script
    assert "live_db_sha256_unchanged" in script
    assert "caddy_changed = $false" in script
    assert "live_default_changed = $false" in script
    assert 'sudo systemctl restart "$SERVICE_NAME"' in script
    assert "systemctl restart prism.service" not in script
    assert "systemctl reload caddy" not in script.lower()
    assert "caddy reload" not in script.lower()


def test_t039_t040_t041_docs_are_current_and_hand_off_to_completed_cutover_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    deploy_pi = DEPLOY_PI_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    for task_id, contract in CONTRACTS.items():
        row = next(line for line in todo.splitlines() if line.startswith(f"| {task_id} "))
        assert row.endswith("| Done |")
        assert contract.name in todo

    assert "T039/T040/T041 Go package and Pi staging gate is complete" in architecture
    assert "Go T039/T040/T041" in schema
    assert "prism-go-primary-staging.service" in deploy_pi
    assert "Windows Package and Pi Staging" in readme
    assert "T039/T040/T041" in go_report
    assert "T042" in todo
    t042_row = next(line for line in todo.splitlines() if line.startswith("| T042 "))
    assert t042_row.endswith("| Done |")
    t045_row = next(line for line in todo.splitlines() if line.startswith("| T045 "))
    t046_row = next(line for line in todo.splitlines() if line.startswith("| T046 "))
    assert t045_row.endswith("| Done |")
    assert t046_row.endswith("| Todo |")
