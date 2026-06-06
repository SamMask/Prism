import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-b-next-notes-live-default-media-boundary.json"
B_NEXT_1_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-b-next-notes-write-bundle.json"
RUNTIME_CLOSURE_PATH = ROOT / "docs" / "contracts" / "phase23-python-runtime-ownership-closure.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
CRUD_PATH = ROOT / "routes" / "notes" / "crud.py"
BATCH_PATH = ROOT / "routes" / "notes" / "batch.py"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_b_next_2_records_no_promotion_decision_without_runtime_changes():
    contract = _contract()

    assert contract["phase"] == "B-next.2"
    assert contract["status"] == "completed_decision_no_promotion"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-b-next-notes-write-bundle.json"
    assert contract["decision"]["promote_notes_bundle_to_live_default_owner"] is False
    assert "copied-DB only" in contract["decision"]["reason"]
    assert "live/default ownership" in contract["decision"]["simple_explanation"]
    assert all(changed is False for changed in contract["runtime_changes"].values())
    assert contract["ownership_boundary_after_b_next_2"]["notes_bundle_go_status"] == "local_copied_db_candidate_only"
    assert contract["ownership_boundary_after_b_next_2"]["b_completion_status_after_final_closure"] == "closed_retained_python"


def test_b_next_2_media_cleanup_boundary_points_to_current_python_owner():
    contract = _contract()
    crud = CRUD_PATH.read_text(encoding="utf-8")
    batch = BATCH_PATH.read_text(encoding="utf-8")
    boundary = contract["media_cleanup_boundary"]

    assert "routes/notes/crud.py::_cleanup_note_images" in boundary["current_python_entrypoints"]
    assert "routes/notes/batch.py::batch_delete_notes" in boundary["current_python_entrypoints"]
    assert "def _cleanup_note_images" in crud
    assert "_cleanup_note_images(existing['content'], existing['cover_image'], note_id)" in crud
    assert "ref_count = db.execute" in crud
    assert "os.remove(filepath)" in crud
    assert "thumb_name = f\"{name_without_ext}_thumb.webp\"" in crud
    assert "from .crud import _cleanup_note_images" in batch
    assert "_cleanup_note_images(note['content'], note['cover_image'], note['id'])" in batch
    assert "copied-DB parity alone cannot prove" in boundary["simple_explanation"]


def test_b_next_2_updates_prior_contracts_without_opening_b_next_3():
    b_next_1 = json.loads(B_NEXT_1_CONTRACT_PATH.read_text(encoding="utf-8"))
    runtime = json.loads(RUNTIME_CLOSURE_PATH.read_text(encoding="utf-8"))
    next_detail = b_next_1["executed_followup_decision"]
    after_b_next_1 = runtime["executed_notes_promotion_decision"]

    assert "recommended_next_detail" not in b_next_1
    assert next_detail["id"] == "B-next.2"
    assert next_detail["status_after_execution"] == "completed_decision_no_promotion"
    assert next_detail["result_contract"] == "docs/contracts/phase23-b-next-notes-live-default-media-boundary.json"
    assert next_detail["no_auto_next_detail"] is True
    assert "not promote" in next_detail["decision"].lower()

    assert "recommended_next_detail_after_b_next_1" not in runtime
    assert after_b_next_1["id"] == "B-next.2"
    assert after_b_next_1["status_after_execution"] == "completed_decision_no_promotion"
    assert after_b_next_1["no_auto_next_detail"] is True
    assert "stops the automatic B-next chain" in after_b_next_1["simple_explanation"]

    assert _contract()["no_auto_next_detail"] is True
    assert "Create B-next.3 automatically" in _contract()["not_authorized_by_b_next_2"]
    assert "Create any automatic B-next item" in _contract()["not_authorized_by_b_next_2"]


def test_docs_record_reason_simple_explanation_and_no_auto_next_detail():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "B-next.2 Notes bundle live/default ownership decision and media-cleanup boundary" in todo
    assert "completed_decision_no_promotion" in todo
    assert "原因：B-next.1 只有 local/copied-DB parity" in todo
    assert "簡易說明：Go 現在能在測試 DB 改 notes" in todo
    assert "No B-next.3 added" in todo
    assert "B final closure 後不再從這裡延伸任何自動細項" in todo
    assert "B no-Python gaps closed as retained Python（非下一步）" in todo

    assert "Phase 23 B-next.2 Notes bundle live/default ownership decision" in architecture
    assert "No B-next.3 is added automatically" in architecture
    assert "not an active queue" in architecture
    assert "`B-next.2 Notes bundle live/default ownership decision" in go_report
    assert "No B-next.3 is added automatically" in go_report
    assert "not an active queue" in go_report

