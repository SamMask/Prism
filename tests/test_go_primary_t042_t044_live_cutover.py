import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = {
    "T042": ROOT / "docs" / "contracts" / "go-primary-live-cutover.json",
    "T043": ROOT / "docs" / "contracts" / "go-primary-rollback-drill.json",
    "T044": ROOT / "docs" / "contracts" / "go-primary-soak-window.json",
}
OPS_SCRIPT = ROOT / "scripts" / "go_primary_pi_live_ops.ps1"
GO_SMOKE = ROOT / "scripts" / "go_primary_full_workflow_smoke.py"
PYTHON_SMOKE = ROOT / "scripts" / "python_live_workflow_smoke.py"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
DEPLOY_PI_PATH = ROOT / "DEPLOY-PI.md"
GO_README_PATH = ROOT / "go-shadow" / "README.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"


def _contract(task_id):
    return json.loads(CONTRACTS[task_id].read_text(encoding="utf-8"))


def test_t042_t043_t044_contracts_record_live_cutover_rollback_and_soak():
    t042 = _contract("T042")
    t043 = _contract("T043")
    t044 = _contract("T044")

    assert t042["status"] == "completed_live_cutover"
    assert t042["execution_target"]["service"] == "prism-go-primary.service"
    assert t042["execution_target"]["addr"] == "127.0.0.1:5004"
    assert t042["cutover"]["caddy_route_header"] == "X-Prism-Go-Primary: hit"
    assert t042["post_cutover_state"]["python_prism"] == "inactive"
    assert t042["post_cutover_state"]["python_service_receives_caddy_traffic"] is False
    assert t042["full_workflow_smoke"]["status"] == "passed"
    assert t042["next_recommended_task"]["id"] == "T043"

    assert t043["status"] == "completed_rollback_drill"
    assert t043["rollback_target"]["service"] == "prism.service"
    assert t043["rollback_target"]["caddy_header"] == "X-Prism-Python-Rollback: hit"
    assert t043["restore_evidence"]["db_matches_backup"] is True
    assert t043["restore_evidence"]["data_matches_pre_cutover"] is True
    assert t043["python_live_smoke"]["status"] == "passed"
    assert t043["post_rollback_state"]["python_prism"] == "active"
    assert t043["next_recommended_task"]["id"] == "T044"

    assert t044["status"] == "completed_soak_window"
    assert t044["pre_soak"]["full_workflow_smoke"] == "passed"
    assert t044["pre_soak"]["smoke_mutation_restored_from_backup"] is True
    assert t044["soak"]["samples"] == 5
    assert t044["soak"]["go_primary_errors_since_start"] == []
    assert t044["soak"]["caddy_errors_since_start"] == []
    assert t044["soak"]["memory_not_higher_than_retained_python_baseline"] is True
    assert t044["final_live_state"]["go_primary"] == "active"
    assert t044["final_live_state"]["python_prism"] == "inactive"
    assert t044["final_live_state"]["migration_pending"] == []
    assert t044["next_recommended_task"]["id"] == "T045"


def test_live_ops_scripts_keep_backup_restore_and_no_public_bind_boundaries():
    ops_script = OPS_SCRIPT.read_text(encoding="utf-8")
    go_smoke = GO_SMOKE.read_text(encoding="utf-8")
    python_smoke = PYTHON_SMOKE.read_text(encoding="utf-8")

    assert 'HostAlias = "PI5Mask24"' in ops_script
    assert "prism-go-primary.service" in ops_script
    assert "--addr 127.0.0.1:$PORT" in ops_script
    assert "PRISM_GO_ALLOW_PUBLIC_BIND" not in ops_script
    assert "PRISM_GO_ALLOW_PROD_DB=1" in ops_script
    assert "X-Prism-Go-Primary hit" in ops_script
    assert "X-Prism-Python-Rollback hit" in ops_script
    assert "sqlite3.connect(sys.argv[1])" in ops_script
    assert "src.backup(dst)" in ops_script
    assert "data-files.tar.gz" in ops_script
    assert "db_matches_backup" in ops_script
    assert "journalctl -u \"$SERVICE_NAME\"" in ops_script
    assert "not_higher_than_retained_python_baseline" in ops_script

    for smoke in (go_smoke, python_smoke):
        assert "import flask" not in smoke.lower()
        assert "from app import" not in smoke
        assert "--insecure" in smoke
        assert "deleted_after_download" in smoke
        assert "/api/server/backup/" in smoke


def test_t042_t043_t044_docs_are_current_and_hand_off_to_t045_t046():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    deploy_pi = DEPLOY_PI_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    for task_id, contract_path in CONTRACTS.items():
        row = next(line for line in todo.splitlines() if line.startswith(f"| {task_id} "))
        assert row.endswith("| Done |")
        assert contract_path.name in todo

    t045_row = next(line for line in todo.splitlines() if line.startswith("| T045 "))
    t046_row = next(line for line in todo.splitlines() if line.startswith("| T046 "))
    t051_row = next(line for line in todo.splitlines() if line.startswith("| T051 "))
    t052_row = next(line for line in todo.splitlines() if line.startswith("| T052 "))
    t053_row = next(line for line in todo.splitlines() if line.startswith("| T053 "))
    assert t045_row.endswith("| Done |")
    assert t046_row.endswith("| Done |")
    assert t051_row.endswith("| Done |")
    assert t052_row.endswith("| Done |")
    assert t053_row.endswith("| Done |")

    assert "T042-T044 Go primary live cutover, rollback, and soak gates are complete" in architecture
    assert "Go T042/T043/T044" in schema
    assert "go_primary_pi_live_ops.ps1" in deploy_pi
    assert "Live Go Primary Cutover, Rollback, and Soak" in readme
    assert "T042/T043/T044 now move Pi live/default ownership to Go primary" in go_report
    assert "T045 removes the Python packaged runtime/startup path" in go_report
