import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-packaged-runtime-release-candidate.json"
B_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-python-runtime-ownership-closure.json"
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
GO_TEST_PATH = ROOT / "go-shadow" / "main_test.go"
BUILD_SCRIPT_PATH = ROOT / "scripts" / "build_go_runtime.ps1"
SMOKE_SCRIPT_PATH = ROOT / "scripts" / "smoke_go_local_artifact.ps1"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_c_contract_records_completed_release_candidate_without_next_detail():
    contract = _contract()
    b_contract = json.loads(B_CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["phase"] == "python-packaging-removal-C"
    assert contract["status"] == "completed_release_candidate"
    assert contract["explicit_user_approval"] is True
    assert contract["no_auto_next_detail"] is True
    assert contract["no_c_next"] is True
    assert "allowed_next_step" not in contract
    assert "recommended_next_detail" not in contract
    assert "Create C-next automatically" in contract["not_authorized_by_C"]
    assert "Create any automatic next detail" in contract["not_authorized_by_C"]
    assert b_contract["status"] == "completed_final_retained_python_closure"
    assert b_contract["final_closure"]["no_start_c_d_e_from_b_closure"] is True


def test_c_artifact_contract_uses_go_artifacts_external_data_and_no_python_packaging():
    contract = _contract()
    rc = contract["release_candidate"]
    build_script = BUILD_SCRIPT_PATH.read_text(encoding="utf-8")

    assert rc["windows_artifact"] == "build/go-runtime/prism-go-runtime.exe"
    assert rc["linux_arm64_artifact"] == "build/go-runtime/prism-go-runtime-linux-arm64"
    assert rc["python_or_venv_required_by_artifact"] is False
    assert rc["external_data_dir_required"] is True
    assert rc["source_db_hash_guard"] is True
    assert "go build -o (Join-Path $outDir \"prism-go-runtime.exe\") ." in build_script
    assert "GOOS = \"linux\"" in build_script
    assert "GOARCH = \"arm64\"" in build_script
    assert "CGO_ENABLED = \"0\"" in build_script
    assert "python" not in build_script.lower()
    assert "pyinstaller" not in build_script.lower()
    assert "venv" not in build_script.lower()


def test_go_runtime_adds_read_only_migration_status_for_c_smoke():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    main_test = GO_TEST_PATH.read_text(encoding="utf-8")

    assert 'mux.HandleFunc("/api/system/migration-status", srv.handleMigrationStatus)' in main_go
    assert "func (s *server) handleMigrationStatus" in main_go
    assert "migrationDefinitions" in main_go
    assert '{16, "normalize_editor_layout", []string{' in main_go
    assert "UPDATE Notes SET editor_layout = 'single'" in main_go
    assert '"current_version": status.CurrentVersion' in main_go
    assert '"latest_version":  status.LatestVersion' in main_go
    assert '"pending":         pending' in main_go
    assert "TestMigrationStatusHandlerMatchesPythonShapeAndKeepsQueryOnly" in main_test
    assert "migration status must keep DB writes blocked" in main_test


def test_c_smoke_script_covers_migration_file_read_write_thumbnail_and_guards():
    contract = _contract()
    smoke = SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    coverage = contract["artifact_smoke_coverage"]

    assert "prism-go-runtime-linux-arm64" in smoke
    assert "Missing linux/arm64 Go artifact" in smoke
    assert "/api/system/migration-status" in smoke
    assert "Migration-status smoke failed" in smoke
    assert "Add-AttachmentFixture" in smoke
    assert "seed_attachment_fixture.go" in smoke
    assert "--enable-attachment-text-read" in smoke
    assert "Attachment text read smoke failed" in smoke
    assert "Default runtime unexpectedly accepted attachment text read candidate route" in smoke
    assert "--enable-tag-write" in smoke
    assert "--enable-category-write" in smoke
    assert "--enable-notes-write" in smoke
    assert "--thumbnail-input" in smoke
    assert "--thumbnail-output" in smoke
    assert "Production/source DB hash changed during local smoke" in smoke
    assert "Refusing to clean smoke path outside repo build/" in smoke
    assert "GET /api/system/migration-status returns current_version" in coverage["migration_status"][0]
    assert "GET /api/attachments/<id> reads a copied text attachment" in coverage["file_read_candidate"][2]
    assert "Built artifact encodes a local PNG to _thumb.webp" in coverage["thumbnail"][0]


def test_docs_record_c_closure_without_starting_d_or_e():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "C. Go packaged runtime release candidate — completed_release_candidate" in todo
    assert "docs/contracts/phase23-go-packaged-runtime-release-candidate.json" in todo
    assert "未啟動 D/E、未新增 C-next" in todo
    assert "C / D / E are not automatic follow-ups from this B closure" in architecture
    assert "Phase 23 C Go packaged runtime release candidate is complete as `completed_release_candidate`" in architecture
    assert "did not deploy Pi, edit Caddy/systemd" in architecture
    assert "`C. Go packaged runtime release candidate` is complete as `completed_release_candidate`" in go_report
    assert "did not deploy Pi, edit Caddy/systemd" in go_report

