import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-write-surface-selection.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_ROADMAP_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
PHASE23_FILE_READ_IMPLEMENTATION_PATH = (
    ROOT / "docs" / "contracts" / "phase23-go-file-read-parity-implementation.json"
)


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def candidates_by_id(contract: dict) -> dict:
    return {candidate["id"]: candidate for candidate in contract["candidate_matrix"]}


def test_phase23_3_is_plan_only_and_depends_on_23_2_contract():
    contract = load_contract()
    prior = json.loads(PHASE23_FILE_READ_IMPLEMENTATION_PATH.read_text(encoding="utf-8"))

    assert contract["phase"] == "23.3"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["plan_only"] is True
    assert contract["runtime_change"] is False
    assert contract["go_write_implementation"] is False
    assert contract["live_execution_authorized"] is False
    assert contract["source_contract"] == "docs/contracts/phase23-go-file-read-parity-implementation.json"
    assert prior["phase"] == "23.2"


def test_selected_first_write_candidate_is_tag_rename_only():
    contract = load_contract()
    selected = contract["selected_candidate"]
    tag_rename = candidates_by_id(contract)["tag_rename"]

    assert selected["id"] == "tag_rename"
    assert selected["route"] == "PUT /api/tags/<tag_id>"
    assert selected["go_owner_after_23_3"] is False
    assert tag_rename["decision"] == "selected_for_23_4"
    assert tag_rename["source"] == "routes/tags.py"
    assert tag_rename["db_side_effects"] == ["Tags.name update only"]
    assert tag_rename["file_side_effects"] == []
    assert tag_rename["external_side_effects"] == []
    assert tag_rename["process_side_effects"] == []
    assert tag_rename["request_schema"] == {"name": "non-empty string after trim"}
    assert tag_rename["success_response"] == {"status": "success"}


def test_rejected_and_deferred_candidates_keep_first_write_narrow():
    candidates = candidates_by_id(load_contract())

    assert candidates["category_create"]["decision"] == "deferred"
    assert candidates["category_update"]["decision"] == "deferred"
    assert candidates["category_delete"]["decision"] == "rejected_for_first_write"
    assert candidates["tag_delete"]["decision"] == "rejected_for_first_write"
    assert candidates["tag_merge"]["decision"] == "rejected_for_first_write"
    assert candidates["notes_core_writes"]["decision"] == "rejected_for_first_write"
    assert candidates["notes_actions_pin_archive"]["decision"] == "deferred"
    assert candidates["notes_duplicate_reorder_batch"]["decision"] == "rejected_for_first_write"
    assert candidates["attachments_and_file_routes"]["decision"] == "rejected_for_first_write"
    assert (
        candidates["uploads_cleanup_import_export_system_server_config"]["decision"]
        == "rejected_for_first_write"
    )


def test_23_4_contract_requires_python_parity_and_db_state_invariants():
    contract = load_contract()["first_write_contract_for_23_4"]

    assert "PUT /api/tags/<tag_id>" in contract["allowed_scope"]
    assert "required string" in contract["request_schema"]["name"]
    assert "400 missing JSON body or name" in contract["response_schema"]["errors"]
    assert "404 missing tag id" in contract["response_schema"]["errors"]
    assert "409 duplicate tag name" in contract["response_schema"]["errors"]
    assert "Update exactly one Tags row." in contract["transaction_semantics"]
    assert "Only Tags.name may change on success." in contract["state_invariants"]
    assert "Note_Tags relationships must not change." in contract["state_invariants"]
    assert "Cover duplicate name 409, including case-insensitive uniqueness behavior." in contract["fixture_plan"]
    assert "Assert rollback leaves Tags unchanged on every failure." in contract["fixture_plan"]


def test_23_3_does_not_authorize_live_or_broader_write_work():
    contract = load_contract()

    blocked = set(contract["not_authorized_by_23_3"])
    assert "Go write implementation" in blocked
    assert "Production DB write" in blocked
    assert "Pi deployment" in blocked
    assert "Caddy route edit or reload" in blocked
    assert "systemd service change" in blocked
    assert "frontend default API target change" in blocked
    assert "live prism-go-readonly.service query_only change" in blocked
    assert "Python route removal" in blocked
    assert "file upload or attachment ownership" in blocked
    assert "public exposure expansion" in blocked

    next_step = contract["allowed_next_step"]
    assert next_step["id"] == "23.4"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["selected_route"] == "PUT /api/tags/<tag_id>"
    assert "live routing remains blocked" in next_step["scope"]


def test_docs_record_23_3_completion_and_23_4_pending_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_roadmap = GO_ROADMAP_PATH.read_text(encoding="utf-8")

    assert "23.3 Go write surface selection gate — ✅ Completed (2026-06-05)" in todo
    assert "docs/contracts/phase23-go-write-surface-selection.json" in todo
    assert "PUT /api/tags/<tag_id>" in todo
    assert "23.4 First Go write route implementation gate — ✅ Completed (2026-06-05)" in todo
    assert "23.5 Go DB-only write expansion gate — ✅ Completed (2026-06-05)" in todo
    assert "23.5 Next DB-only write implementation subgate — ✅ Completed (2026-06-05)" in todo
    assert "Phase 23.3 Go write surface selection gate is complete" in architecture
    assert "Phase 23.4 First Go write route implementation gate is complete" in architecture
    assert "Phase 23.5 Go DB-only write expansion gate is complete" in architecture
    assert "Phase 23.5-next.1 Second Go DB-only write implementation subgate is complete" in architecture
    assert "Phase 23.5-next.2-4 category update closure is complete" in architecture
    assert "Phase 23.6 File / attachment ownership gate is complete as a plan-only inventory and selection gate" in architecture
    assert "Phase 23.6-next First Go file-read route implementation candidate is complete" in architecture
    assert "Phase 23.7 Migration / DB ownership decision gate is complete as plan-only" in architecture
    assert "Phase 23.9 Pi deployment rollout is complete" in architecture
    assert "Phase 23 Go runtime reduction track is closed with retained-Python normal path" in architecture
    assert "`23.3 Go write surface selection gate is complete`" in go_roadmap
    assert "`23.4 First Go write route implementation gate is complete`" in go_roadmap
    assert "`23.5 Go DB-only write expansion gate is complete`" in go_roadmap
    assert "`23.6-next First Go file-read route implementation candidate` is complete" in go_roadmap
    assert "`23.7 Migration / DB ownership decision gate` is complete as plan-only" in go_roadmap
    assert "`23.9 Pi deployment rollout` is complete" in go_roadmap
    assert "Phase 23 closes with retained Python as the normal runtime path" in go_roadmap
    assert "`23.5-next.1 Second Go DB-only write implementation subgate is complete`" in go_roadmap
    assert "`23.5-next.2-4 Category update parity hardening, rollback lock, and boundary closure is complete`" in go_roadmap

