import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELECTION_PATH = ROOT / "docs" / "contracts" / "phase21-post-push-product-frontend-selection.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"


def _selection():
    return json.loads(SELECTION_PATH.read_text(encoding="utf-8"))


def test_phase21_3_selects_product_frontend_backlog_plan_only():
    selection = _selection()

    assert selection["phase"] == "21.3"
    assert selection["explicit_user_approval"] is True
    assert selection["plan_only"] is True
    assert selection["selected_branch"] == "product_frontend_backlog"
    assert selection["runtime_change_performed"] is False
    assert selection["live_pi_change_performed"] is False
    assert selection["caddy_change_performed"] is False
    assert selection["frontend_default_change_performed"] is False
    assert selection["go_file_read_body_scan_performed"] is False
    assert selection["go_write_file_migration_performed"] is False
    assert selection["public_exposure_change_performed"] is False


def test_phase21_3_records_post_push_truth_and_repo_local_omx_cleanup():
    selection = _selection()
    truth = selection["post_push_truth"]

    assert truth["git_status_short_branch_before_21_3"] == "## main...origin/main"
    assert truth["head_origin_divergence_before_21_3"] == "0 0"
    assert truth["phase21_delivery_commit"].startswith("7255de7 ")
    assert truth["live_pi_verified"] is False

    cleanup = truth["repo_local_omx_removal"]
    assert selection["repo_local_omx_removed"] is True
    assert cleanup["scope"] == "repo-local ignored .omx/ runtime/cache directory only"
    assert cleanup["global_codex_or_oh_my_codex_install_touched"] is False
    assert cleanup["tracked_git_effect"] == "none"
    assert "active Codex/OMX native hooks may recreate ignored .omx/ state" in cleanup["runtime_truth"]


def test_phase21_3_rejects_pi_delivery_and_go_scope_expansion():
    selection = _selection()
    rejected = {item["id"]: item for item in selection["not_selected"]}

    assert "pi_delivery_planning" in rejected
    assert "live preflight" in rejected["pi_delivery_planning"]["reason"]
    assert "go_file_read_parity_assessment" in rejected
    assert "file-read safety" in rejected["go_file_read_parity_assessment"]["reason"]
    assert "go_write_file_migration_expansion" in rejected


def test_phase21_3_product_frontend_intake_keeps_existing_contracts():
    selection = _selection()
    intake = selection["product_frontend_intake"]

    assert "docs/FRONTEND-REDESIGN-PLAN.md" in intake["source_docs"]
    assert intake["selection_rule"].startswith("Start with a read-only")
    assert "Current frontend route and workflow inventory" in intake["allowed_assessment_scope"]
    assert "Reading/editor workflow gaps that preserve existing Preview Editing UX" in intake["allowed_assessment_scope"]

    forbidden = intake["not_allowed_by_21_3"]
    assert "Frontend default API target change" in forbidden
    assert "New backend API or schema implementation" in forbidden
    assert "Server-side UI preference persistence" in forbidden
    assert "AI/ML, collaboration, realtime, plugin platform, or collections schema" in forbidden
    assert "Go file-read/body scan or Go write/file/migration implementation" in forbidden


def test_phase21_3_next_step_is_22_0_product_frontend_intake_gate():
    selection = _selection()
    next_step = selection["allowed_next_step"]

    assert next_step["id"] == "22.0"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert next_step["scope"].startswith("Plan-only read-only audit")
    assert "Frontend implementation" in next_step["not_authorized_without_approval"]
    assert "New backend API or DB schema" in next_step["not_authorized_without_approval"]
    assert "Pi deploy or live service reload" in next_step["not_authorized_without_approval"]


def test_phase21_3_todo_records_branch_choice_and_phase22_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "21.3 Post-push Delivery Decision Gate" in todo
    assert "product/frontend backlog" in todo
    assert "docs/contracts/phase21-post-push-product-frontend-selection.json" in todo
    assert "Phase 22: Product Frontend Backlog Intake" in todo
    assert "22.0 Product Frontend Backlog Intake Gate" in todo

