import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-local-smoke-artifact-release-boundary.json"
SOURCE_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-local-packaging-thumbnail-plan.json"
SMOKE_SCRIPT_PATH = ROOT / "scripts" / "smoke_go_local_artifact.ps1"
BUILD_SCRIPT_PATH = ROOT / "scripts" / "build_go_runtime.ps1"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_23_8_2_23_8_3_contract_records_local_only_artifact_smoke():
    contract = _contract()
    source = json.loads(SOURCE_CONTRACT_PATH.read_text(encoding="utf-8"))
    smoke = contract["local_smoke_artifact"]

    assert contract["phase"] == "23.8.2-23.8.3"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-go-local-packaging-thumbnail-plan.json"
    assert source["allowed_next_steps"][0]["id"] == "23.8.2"
    assert contract["runtime_change"] == "local_build_and_smoke_script_only"
    assert contract["packaged_artifact_created_by_validation"] is True
    assert contract["live_execution_authorized"] is False
    assert contract["production_db_write"] is False
    assert contract["production_filesystem_mutation"] is False
    assert contract["caddy_or_service_change"] is False
    assert contract["pi_deploy"] is False
    assert contract["frontend_default_api_target_change"] is False
    assert smoke["script"] == "scripts/smoke_go_local_artifact.ps1"
    assert smoke["artifact"] == "build/go-runtime/prism-go-runtime.exe"
    assert smoke["evidence_file"] == "build/go-local-smoke/evidence.json"


def test_local_smoke_script_uses_copied_db_and_guards_production_source():
    contract = _contract()
    data_rule = contract["local_smoke_artifact"]["data_rule"]
    script = SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")

    assert data_rule["source_db"] == "knowledge.db may be read only to create a copied smoke DB"
    assert data_rule["go_runtime_refuses_direct_knowledge_db"] is True
    assert data_rule["source_db_sha256_guard"] is True
    assert data_rule["smoke_cleanup_scope"] == "repo build/ only"
    assert "Assert-UnderBuild" in script
    assert "Refusing to clean smoke path outside repo build/" in script
    assert "prism_local_smoke_read_dev.db" in script
    assert "prism_local_smoke_write_dev.db" in script
    assert "Get-FileHash -Algorithm SHA256" in script
    assert "Production/source DB hash changed during local smoke" in script
    assert "Remove-Item -LiteralPath $smokeRootPath -Recurse -Force" in script


def test_local_smoke_covers_startup_spa_read_and_flag_gated_write_candidates():
    contract = _contract()
    read_smoke = contract["local_smoke_artifact"]["read_only_smoke"]
    write_smoke = contract["local_smoke_artifact"]["write_candidate_smoke"]
    thumbnail_smoke = contract["local_smoke_artifact"]["thumbnail_helper_smoke"]
    script = SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    build_script = BUILD_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "npm run build" in build_script
    assert "go build -o (Join-Path $outDir \"prism-go-runtime.exe\") ." in build_script
    assert read_smoke["sqlite_query_only"] is True
    assert read_smoke["api_surface"] == "get-read-only"
    assert "serve embedded SPA index.html" in read_smoke["checks"]
    assert "PUT /api/tags/<id> remains 405 when write flag is disabled" in read_smoke["checks"]
    assert "POST /api/notes remains 405 when notes write flag is disabled" in read_smoke["checks"]
    assert write_smoke["flags"] == ["--enable-tag-write", "--enable-category-write", "--enable-notes-write"]
    assert write_smoke["sqlite_query_only"] is False
    assert write_smoke["db_scope"] == "copied smoke DB only"
    assert "PUT /api/tags/<id> succeeds against copied DB" in write_smoke["checks"]
    assert "PUT /api/categories/<id> succeeds against copied DB" in write_smoke["checks"]
    assert "POST /api/notes succeeds against copied DB" in write_smoke["checks"]
    assert "PUT /api/notes/<id> creates history against copied DB" in write_smoke["checks"]
    assert "GET /api/notes/<id>/history succeeds against copied DB" in write_smoke["checks"]
    assert "DELETE /api/notes/<id> succeeds against copied DB" in write_smoke["checks"]
    assert "--enable-tag-write" in script
    assert "--enable-category-write" in script
    assert "--enable-notes-write" in script
    assert "/api/notes?per_page=1" in script
    assert "Default runtime unexpectedly accepted write candidate route" in script
    assert "Default runtime unexpectedly accepted notes write candidate route" in script
    assert "Notes create smoke failed" in script
    assert "Notes update smoke failed" in script
    assert "Notes history smoke failed" in script
    assert "Notes delete smoke failed" in script
    assert thumbnail_smoke["flags"] == ["--thumbnail-input", "--thumbnail-output"]
    assert thumbnail_smoke["output_convention"] == "_thumb.webp"
    assert "built Go artifact encodes a local PNG to _thumb.webp" in thumbnail_smoke["checks"]
    assert "pillow_closure_thumb.webp" in script
    assert "--thumbnail-input" in script
    assert "--thumbnail-output" in script
    assert "RIFF" in script and "WEBP" in script


def test_release_boundary_blocks_pi_caddy_systemd_and_python_removal():
    contract = _contract()
    boundary = contract["release_boundary"]
    blocked = set(contract["not_authorized_by_23_8_2_23_8_3"])

    assert boundary["pi_rollout_owner"] == "23.9 Pi deployment rollout track"
    assert "Raspberry Pi has been updated" in boundary["local_packaging_success_does_not_mean"]
    assert "Caddy route has been changed or reloaded" in boundary["local_packaging_success_does_not_mean"]
    assert "systemd service has been changed or restarted" in boundary["local_packaging_success_does_not_mean"]
    assert "production knowledge.db has been written" in boundary["local_packaging_success_does_not_mean"]
    assert boundary["next_pi_gate"]["id"] == "23.9.1"
    assert boundary["next_pi_gate"]["requires_explicit_user_approval"] is True
    assert "service status" in boundary["next_pi_gate"]["minimum_checks"]
    assert "Caddy validate" in boundary["next_pi_gate"]["minimum_checks"]
    assert "DB backup" in boundary["next_pi_gate"]["minimum_checks"]
    assert "route ownership check" in boundary["next_pi_gate"]["minimum_checks"]
    assert "Pi deployment" in blocked
    assert "Caddy route edit or reload" in blocked
    assert "systemd service change or restart" in blocked
    assert "Production knowledge.db write" in blocked
    assert "Python runtime removal" in blocked


def test_docs_record_23_8_2_23_8_3_completion_and_next_gate():
    contract = _contract()
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert contract["allowed_next_step"]["id"] == "23.9.1"
    assert contract["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "23.8 Local packaging execution track — ✅ Completed (2026-06-06)" in todo
    assert "23.8.2** Local smoke artifact" in todo
    assert "scripts/smoke_go_local_artifact.ps1" in todo
    assert "docs/contracts/phase23-go-local-smoke-artifact-release-boundary.json" in todo
    assert "23.8.3** Release boundary" in todo
    assert "本機封裝可用不代表 Pi 已更新" in todo
    assert "Phase 23.8.2 Local smoke artifact is complete" in architecture
    assert "Phase 23.8.3 Release boundary is complete" in architecture
    assert "Phase 23.9 Pi deployment rollout is complete" in architecture
    assert "Phase 23 Go runtime reduction track is closed with retained-Python normal path" in architecture
    assert "`23.8.2 Local smoke artifact` is complete" in go_report
    assert "`23.8.3 Release boundary` is complete" in go_report
    assert "`23.9 Pi deployment rollout` is complete" in go_report
    assert "Phase 23 closes with retained Python as the normal runtime path" in go_report
