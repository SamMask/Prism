import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-live-cutover-rollback-proof.json"
C_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-packaged-runtime-release-candidate.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_d_contract_records_completed_rollback_proof_without_next_detail():
    contract = _contract()
    c_contract = json.loads(C_CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["phase"] == "python-packaging-removal-D"
    assert contract["status"] == "completed_rollback_proof_no_permanent_cutover"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-go-packaged-runtime-release-candidate.json"
    assert contract["no_auto_next_detail"] is True
    assert contract["no_d_next"] is True
    assert "allowed_next_step" not in contract
    assert "recommended_next_detail" not in contract
    assert c_contract["status"] == "completed_release_candidate"


def test_d_proves_temporary_cutover_and_restores_retained_python_owner():
    contract = _contract()

    assert contract["result"]["permanent_cutover"] is False
    assert contract["result"]["rollback_completed"] is True
    assert contract["result"]["normal_runtime_owner_after_D"] == "retained Python prism.service"
    assert "upload/delete/cleanup/import/export/server/migration-runner" in contract["result"]["reason_no_permanent_cutover"]
    assert contract["temporary_cutover"]["artifact_sha256"] == "be2681ae95abba505493f36f7e93ec591406eecb2dcd6c1440afdc0d95a50fa7"
    assert contract["temporary_cutover"]["production_db_write_flags"] is False
    assert contract["temporary_cutover"]["sqlite_query_only"] is True
    assert contract["rollback_evidence"]["migration_status_route_removed_from_go_matcher"] is True
    assert contract["rollback_evidence"]["db_backup_sha256"] == contract["rollback_evidence"]["db_after_rollback_sha256"]
    assert "Full Go runtime ownership" in contract["not_promoted_by_D"]
    assert "Create D-next automatically" in contract["not_promoted_by_D"]


def test_d_live_evidence_keeps_route_ownership_truthful():
    contract = _contract()
    go_headers = contract["live_cutover_evidence"]["go_routed_headers"]
    python_headers = contract["live_cutover_evidence"]["python_retained_headers"]

    assert "x-prism-go-read-routing: hit" in go_headers["GET /api/system/migration-status"]
    assert "x-prism-go-read-routing: hit" in go_headers["GET /api/notes?per_page=1"]
    assert "no x-prism-go-read-routing header" in python_headers["GET /api/export/json"]
    assert "no x-prism-go-read-routing header" in python_headers["GET /api/export/markdown"]
    assert "no x-prism-go-read-routing header" in python_headers["POST /api/upload without Origin"]
    assert "no x-prism-go-read-routing header" in python_headers["POST /api/notes/import/md without Origin"]
    assert contract["live_cutover_evidence"]["migration_status"]["current_version"] == 16
    assert contract["live_cutover_evidence"]["migration_status"]["pending"] == []


def test_docs_record_d_closure_without_starting_e_or_d_next():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "D. Live cutover and rollback proof — completed_rollback_proof_no_permanent_cutover" in todo
    assert "docs/contracts/phase23-go-live-cutover-rollback-proof.json" in todo
    assert "No D-next added" in todo
    assert "Phase 23 D Live cutover and rollback proof is complete as `completed_rollback_proof_no_permanent_cutover`" in architecture
    assert "D did not promote a permanent full Go cutover" in architecture
    assert "`D. Live cutover and rollback proof` is complete as `completed_rollback_proof_no_permanent_cutover`" in go_report
    assert "No D-next is added" in go_report

