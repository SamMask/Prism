import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-local-packaging-thumbnail-plan.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
REQUIREMENTS_PATH = ROOT / "requirements.txt"
UPLOAD_ROUTE_PATH = ROOT / "routes" / "upload.py"
GO_MOD_PATH = ROOT / "go-shadow" / "go.mod"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_23_8_1_contract_is_plan_only_and_keeps_runtime_unchanged():
    contract = _contract()
    runtime = contract["runtime_changes"]
    blocked = contract["blocked_scope"]

    assert contract["phase"] == "23.8.1"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["scope_type"] == "plan_only"
    assert runtime["go_code_changed"] is False
    assert runtime["python_code_changed"] is False
    assert runtime["pillow_removed"] is False
    assert runtime["go_webp_encoder_added"] is False
    assert runtime["packaged_artifact_created"] is False
    assert runtime["pi_deployed"] is False
    assert "Remove Pillow from requirements.txt" in blocked
    assert "Add a Go WebP encoder dependency" in blocked
    assert "Implement Go upload or thumbnail routes" in blocked
    assert "Deploy to Pi" in blocked


def test_local_packaging_contract_preserves_external_data_and_python_migration_owner():
    contract = _contract()
    packaging = contract["local_packaging_contract"]
    data_dir = packaging["data_dir"]
    migration = packaging["migration_owner"]

    assert packaging["binary_owner"] == "Go local artifact candidate"
    assert data_dir["required"] is True
    assert data_dir["external_to_binary"] is True
    assert data_dir["production_db_rule"].startswith("local artifact smoke must use a copied DB")
    for required_path in [
        "knowledge.db",
        "knowledge.db-wal",
        "knowledge.db-shm",
        "static/uploads",
        "docs/attachments",
        "logs",
        "backups",
        "config/env",
    ]:
        assert required_path in data_dir["owns"]
    assert migration["normal_live_owner"] == (
        "Python migrations.run_migrations() and Python /api/system/migration-status"
    )
    assert migration["go_allowed"] == "status-only local/readiness candidate with SQLite query_only"
    assert "Schema_Meta writes" in migration["go_forbidden"]
    assert "live migration runner ownership" in migration["go_forbidden"]


def test_thumbnail_plan_records_current_pillow_contract_and_future_go_gate():
    contract = _contract()
    thumbnail = contract["thumbnail_webp_plan"]
    current = thumbnail["current_contract"]
    dependency_gate = thumbnail["dependency_decision_gate"]
    removal_gate = thumbnail["pillow_removal_gate"]

    assert thumbnail["current_owner"] == "Python upload/import thumbnail generation through optional Pillow"
    assert "POST /api/upload" in current["routes"]
    assert "POST /api/upload/url" in current["routes"]
    assert "note import image download helper" in current["routes"]
    assert current["input_mimes"] == [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    ]
    assert current["output_convention"] == "static/uploads/<timestamp>_<name>_thumb.webp"
    assert current["max_width_px"] == 500
    assert current["quality"] == 80
    assert thumbnail["planned_go_owner"].endswith("not implemented in 23.8.1")
    assert dependency_gate["required"] is True
    assert dependency_gate["no_dependency_selected_in_this_gate"] is True
    assert "WebP encode support, not decode-only support" in dependency_gate["must_verify"]
    assert "Raspberry Pi arm64 build" in dependency_gate["must_verify"]
    assert removal_gate["blocked_in_23_8_1"] is True
    assert "Go encoder dependency decision is complete" in removal_gate["allowed_only_after"]


def test_docs_record_23_8_1_completion_and_next_subgates():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.8 Local packaging execution track — ✅ Completed (2026-06-06)" in todo
    assert "23.8.1** Packaging contract + thumbnail ownership plan" in todo
    assert "docs/contracts/phase23-go-local-packaging-thumbnail-plan.json" in todo
    assert "23.8-thumb Go WebP thumbnail ownership / Pillow removal track" in todo
    assert "23.8-thumb.1** WebP encoder dependency decision" in todo
    assert "23.8-thumb.3** Pillow removal gate" in todo
    assert "Phase 23.8.1 Local packaging contract and thumbnail ownership plan is complete as plan-only" in architecture
    assert "Phase 23.8.2 Local smoke artifact is complete" in architecture
    assert "Phase 23.9 Pi deployment rollout is complete" in architecture
    assert "Phase 23 Go runtime reduction track is closed with retained-Python normal path" in architecture
    assert "`23.8.1 Local packaging contract and thumbnail ownership plan` is complete as plan-only" in go_report
    assert "`23.8.2 Local smoke artifact` is complete" in go_report
    assert "`23.9 Pi deployment rollout` is complete" in go_report
    assert "Phase 23 closes with retained Python as the normal runtime path" in go_report


def test_pillow_and_go_webp_dependency_are_not_changed_by_plan_gate():
    requirements = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    upload_route = UPLOAD_ROUTE_PATH.read_text(encoding="utf-8")
    go_mod = GO_MOD_PATH.read_text(encoding="utf-8")

    assert "Pillow" not in requirements
    assert "from PIL import Image" not in upload_route
    assert "generate_webp_thumbnail" in upload_route
    assert "_thumb.webp" in upload_route
    assert "github.com/chai2010/webp" not in go_mod
    assert "github.com/kolesa-team/go-webp" not in go_mod
    assert "nativewebp" not in go_mod
