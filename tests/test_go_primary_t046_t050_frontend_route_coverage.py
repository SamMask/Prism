import json
from pathlib import Path

from tests.go_source_assertions import read_go_package_source


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-frontend-route-coverage.json"
TODO_PATH = ROOT / "docs" / "development-history" / "go-primary-runtime-completion-20260617.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
ARCHITECTURE_HISTORY_PATH = ROOT / "docs" / "development-history" / "architecture-go-migration-history-20261006.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
GO_README_PATH = ROOT / "go-shadow" / "README.md"
GO_SHADOW_DIR = ROOT / "go-shadow"
API_TS_PATH = ROOT / "frontend" / "src" / "services" / "api.ts"
PROMPT_BUILDER_PATH = ROOT / "frontend" / "src" / "hooks" / "usePromptBuilder.ts"
NOTE_FORM_PATH = ROOT / "frontend" / "src" / "hooks" / "editor" / "useNoteForm.ts"
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
UPDATE_SECTION_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "UpdateSection.tsx"
PROMPT_EXTRACTION_PATH = ROOT / "frontend" / "src" / "hooks" / "editor" / "usePromptExtraction.ts"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_t046_contract_records_frontend_to_go_route_coverage_scope():
    contract = _contract()

    assert contract["status"] == "completed"
    assert contract["task_ids"] == ["T046", "T047", "T048", "T049", "T050"]
    assert contract["scope"]["route_manifest_basis"] == "docs/contracts/go-primary-route-ownership-manifest.json"
    assert contract["recommended_next_task"] == "T051"
    decisions = {item["task_id"]: item for item in contract["coverage_decisions"]}
    assert decisions["T047"]["go_surface"] == "POST /api/upload/extract-prompt"
    assert "PRISM-OPT-42" in decisions["T047"]["removed"]
    assert "POST /api/notes/<id>/separate" in decisions["T048"]["go_surface"]
    assert decisions["T049"]["go_surface"] == "GET /api/system/check-update"
    assert "PRISM-OPT-42" in decisions["T049"]["removed"]
    assert decisions["T050"]["old_path"] == "/static/config/wizard_options.json"
    assert decisions["T050"]["new_path"] == "/api/wizard-options"


def test_frontend_no_longer_uses_legacy_static_wizard_options_path():
    prompt_builder = PROMPT_BUILDER_PATH.read_text(encoding="utf-8")
    frontend_src = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "frontend" / "src").rglob("*.ts*"))

    assert 'fetch("/api/wizard-options")' in prompt_builder
    assert "/static/config/wizard_options.json" not in frontend_src


def test_frontend_missing_surfaces_have_visible_or_supported_paths():
    api_ts = API_TS_PATH.read_text(encoding="utf-8")
    note_form = NOTE_FORM_PATH.read_text(encoding="utf-8")
    i18n = I18N_PATH.read_text(encoding="utf-8")

    # PRISM-OPT-42: the dead extract-prompt / check-update callers are deleted, and the
    # unused separation wrappers are gone (the separation routes stay as deprecated API).
    assert "/upload/extract-prompt" not in api_ts
    assert "/system/check-update" not in api_ts
    assert "check_separation" not in api_ts
    assert "`/notes/${noteId}/separate`" not in api_ts
    assert not UPDATE_SECTION_PATH.exists()
    assert not PROMPT_EXTRACTION_PATH.exists()
    assert "`/notes/${noteId}/restore`" in api_ts
    # PRISM-OPT-19: the editor no longer splits long notes after save; the routes stay for API compatibility.
    assert "separateContent" not in note_form
    assert "separationFailed" not in i18n
    assert "silent" not in note_form


def test_go_primary_registers_frontend_called_missing_routes_and_static_guard():
    main_go = read_go_package_source(GO_SHADOW_DIR)

    # PRISM-OPT-42 removed these two routes; the Go 404 behavior is locked by
    # go-shadow/removed_routes_test.go.
    assert '"/api/upload/extract-prompt"' not in main_go
    assert '"/api/system/check-update"' not in main_go
    assert "handleExtractPrompt" not in main_go
    assert "handleCheckUpdate" not in main_go
    assert 'case "check_separation":' in main_go
    assert 'case "separate":' in main_go
    assert 's.restoreSeparatedContent(w, noteID)' in main_go
    assert 'strings.HasPrefix(r.URL.Path, "/static/config/")' in main_go
    assert 'writeError(w, http.StatusNotFound, "Static config is available through API options routes")' in main_go
    assert 'docs", "notes"' in main_go


def test_docs_record_t046_t052_completion_and_t053_handoff():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8") + ARCHITECTURE_HISTORY_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")

    assert "T046-T050 frontend → Go primary route coverage closure 已完成" in todo
    assert "docs/contracts/go-primary-frontend-route-coverage.json" in todo
    for task_id in ("T046", "T047", "T048", "T049", "T050"):
        assert f"| {task_id} |" in todo
        assert f"| {task_id} |" in todo and "| Done |" in todo.split(f"| {task_id} |", 1)[1].splitlines()[0]
    assert "| T051 |" in todo and "| Done |" in todo.split("| T051 |", 1)[1].splitlines()[0]
    assert "| T052 |" in todo and "| Done |" in todo.split("| T052 |", 1)[1].splitlines()[0]
    assert "| T053 |" in todo and "| Done |" in todo.split("| T053 |", 1)[1].splitlines()[0]
    assert "T046-T050 frontend-to-Go route coverage closure is complete" in architecture
    assert "T051 route ownership / API docs current-truth refresh is complete" in architecture
    assert "Migration v17" in schema
    assert "Go runtime 為唯一 migration owner" in schema
    assert "T046-T050 frontend route coverage closure" in readme
