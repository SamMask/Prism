import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_PATH = ROOT / "docs" / "contracts" / "phase23-go-file-read-parity-implementation.json"
PLAN_PATH = ROOT / "docs" / "contracts" / "phase23-go-file-read-parity-plan.json"
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
GO_DIFF_TEST_PATH = ROOT / "tests" / "test_phase18_go_shadow_contract.py"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"


def _implementation():
    return json.loads(IMPLEMENTATION_PATH.read_text(encoding="utf-8"))


def test_phase23_2_records_authorized_local_read_only_scope():
    implementation = _implementation()

    assert implementation["phase"] == "23.2"
    assert implementation["explicit_user_approval"] is True
    assert implementation["source_contract"] == "docs/contracts/phase23-go-file-read-parity-plan.json"
    assert implementation["risk_level"] == "P0 safety-critical"
    assert implementation["implementation_scope"] == "local copied-DB Go read-only text attachment body search parity"
    assert implementation["runtime_change_performed"] is False
    assert implementation["live_pi_change_performed"] is False
    assert implementation["caddy_change_performed"] is False
    assert implementation["frontend_default_change_performed"] is False
    assert implementation["production_db_change_performed"] is False


def test_phase23_2_go_scanner_uses_contract_limits_and_path_safety():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")

    assert "maxAttachmentFileBytes int64 = 1048576" in main_go
    assert "maxAttachmentScanFiles = 200" in main_go
    assert "maxAttachmentScanBytes int64 = 5242880" in main_go
    assert "maxAttachmentScanDuration = 250 * time.Millisecond" in main_go
    assert 'strings.HasPrefix(cleaned, "docs/attachments/")' in main_go
    assert 'ext == "md" || ext == "markdown" || ext == "txt"' in main_go
    assert 'part == ".."' in main_go
    assert "filepath.IsAbs(relativePath)" in main_go
    assert "filepath.VolumeName(relativePath)" in main_go
    assert "filepath.EvalSymlinks" in main_go
    assert "isSubpath(resolved, root)" in main_go


def test_phase23_2_go_search_merges_attachment_body_note_ids_without_write_methods():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")

    assert "buildNotesSearchClause(q)" in main_go
    assert "attachmentContentNoteIDs(keyword)" in main_go
    assert "n.id IN (" in main_go
    assert "SELECT note_id, file_path, file_type" in main_go
    assert "os.ReadFile(resolved)" in main_go
    assert "PRAGMA query_only = ON" in main_go
    assert "http.MethodGet" in main_go
    assert "enableTagWrite" in main_go
    assert "Thumbnail write route is disabled" in main_go
    assert "enableNotesWrite" in main_go
    assert "Notes write route is disabled" in main_go


def test_phase23_2_python_vs_go_diff_fixture_covers_body_hits_and_safety_non_matches():
    diff_test = GO_DIFF_TEST_PATH.read_text(encoding="utf-8")

    assert "bodymdcanary" in diff_test
    assert "bodymarkdowncanary" in diff_test
    assert "bodytxtcanary" in diff_test
    assert "unsupportedbodycanary" in diff_test
    assert "outsidebodycanary" in diff_test
    assert "absolutebodycanary" in diff_test
    assert 'monkeypatch.setattr(app, "root_path", data_dir)' in diff_test
    assert '"--data-dir"' in diff_test


def test_phase23_2_contract_forbids_live_route_and_write_expansion():
    implementation = _implementation()
    forbidden = implementation["not_authorized_by_23_2"]

    assert "Go write/file/migration implementation beyond bounded read-only body scan" in forbidden
    assert "Attachment upload/read/delete/write route ownership" in forbidden
    assert "Caddy route expansion or reload" in forbidden
    assert "Changing prism-go-readonly.service away from SQLite query_only" in forbidden
    assert "Production knowledge.db access or writes from Go" in forbidden
    assert "Pi deploy or live service reload" in forbidden
    assert "Python backend removal" in forbidden
    assert "Direct public internet exposure" in forbidden


def test_phase23_2_next_step_is_plan_only_23_3_write_surface_selection():
    next_step = _implementation()["allowed_next_step"]

    assert next_step["id"] == "23.3"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert next_step["scope"].startswith("Plan-only candidate matrix")
    assert "Go write implementation" in next_step["not_authorized_without_approval"]
    assert "Attachment/file route ownership" in next_step["not_authorized_without_approval"]
    assert "Pi deploy or live service reload" in next_step["not_authorized_without_approval"]


def test_phase23_1_contract_points_to_23_2_before_implementation():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    implementation = _implementation()

    assert plan["allowed_next_step"]["id"] == "23.2"
    assert plan["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert implementation["source_contract"] == "docs/contracts/phase23-go-file-read-parity-plan.json"


def test_phase23_2_docs_record_completion_and_23_3_next_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.2 Go file-read parity implementation gate — ✅ Completed" in todo
    assert "23.3 Go write surface selection gate — ✅ Completed" in todo
    assert "23.4 First Go write route implementation gate — ✅ Completed" in todo
    assert "23.5 Go DB-only write expansion gate — ✅ Completed" in todo
    assert "23.5 Next DB-only write implementation subgate — ✅ Completed" in todo
    assert "Phase 23.2 Go file-read parity implementation gate" in architecture
    assert "Phase 23.3 Go write surface selection gate is complete" in architecture
    assert "Phase 23.4 First Go write route implementation gate is complete" in architecture
    assert "Phase 23.5 Go DB-only write expansion gate is complete" in architecture
    assert "Phase 23.5-next.1 Second Go DB-only write implementation subgate is complete" in architecture
    assert "Phase 23.5-next.2-4 category update closure is complete" in architecture
    assert "23.2 Go file-read parity implementation gate is complete" in go_report
    assert "23.3 Go write surface selection gate is complete" in go_report
    assert "23.4 First Go write route implementation gate is complete" in go_report
    assert "23.5 Go DB-only write expansion gate is complete" in go_report
    assert "23.5-next.1 Second Go DB-only write implementation subgate is complete" in go_report
    assert "23.5-next.2-4 Category update parity hardening, rollback lock, and boundary closure is complete" in go_report

