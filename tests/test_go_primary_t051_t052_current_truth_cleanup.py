import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "contracts" / "go-primary-route-ownership-manifest.json"
API_REFERENCE_PATH = ROOT / "docs" / "API_REFERENCE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
DEPLOYMENT_PATH = ROOT / "docs" / "DEPLOYMENT.md"
DEPLOY_PI_PATH = ROOT / "DEPLOY-PI.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
TODO_PATH = ROOT / "docs" / "TODO.md"
README_PATH = ROOT / "README.md"
DOCS_README_PATH = ROOT / "docs" / "README.md"
CONTRIBUTING_PATH = ROOT / "docs" / "CONTRIBUTING.md"
GO_README_PATH = ROOT / "go-shadow" / "README.md"
INDEX_PATH = ROOT / "docs" / "INDEX.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _todo_row(task_id: str) -> str:
    return next(line for line in _text(TODO_PATH).splitlines() if line.startswith(f"| {task_id} "))


def test_t051_manifest_records_go_primary_current_owner_and_legacy_read_routing_decision():
    manifest = json.loads(_text(MANIFEST_PATH))

    assert manifest["task_id"] == "T004"
    assert manifest["last_refreshed_task_id"] == "T051"
    assert manifest["production_runtime_owner"] == "go-primary"
    assert "Python backend source remains legacy/dev/test context until T053" in manifest["boundary"]
    assert "go_candidate values are historical implementation provenance" in manifest["go_candidate_field_note"]

    routes = {(route["rule"], tuple(route["methods"])): route for route in manifest["routes"]}
    assert routes[("/api/notes", ("POST",))]["production_owner"] == "go-primary"
    assert routes[("/api/upload/extract-prompt", ("POST",))]["production_owner"] == "go-primary"
    assert routes[("/api/system/check-update", ("GET",))]["production_owner"] == "go-primary"
    assert routes[("/", ("GET",))]["go_primary_owner"] == "go-primary embedded SPA/static runtime"

    legacy_route = routes[("/api/system/go-read-routing", ("GET",))]
    assert legacy_route["production_owner"] == "legacy-python-source-only"
    assert "not part of the Go primary product API" in legacy_route["current_owner_note"]
    assert not any(route["production_owner"] == "python" for route in manifest["routes"])


def test_t051_docs_replace_stale_python_owner_wording_with_current_truth():
    api_reference = _text(API_REFERENCE_PATH)
    schema = _text(SCHEMA_PATH)
    deployment = _text(DEPLOYMENT_PATH)
    deploy_pi = _text(DEPLOY_PI_PATH)
    architecture = _text(ARCHITECTURE_PATH)
    go_readme = _text(GO_README_PATH)
    index = _text(INDEX_PATH)

    assert "Go primary live/default runtime" in api_reference
    assert "legacy Flask source-only" in api_reference
    assert "not part of the Go primary product API" in api_reference
    assert "production/default runtime owner 仍是 Python" not in api_reference
    assert "text attachment body search remains Python-owned" not in api_reference

    assert "Go T051" in schema
    assert "Go T052" in schema
    assert "T051 已將 API / route ownership 文件刷新" in deployment
    assert "文件版本**：T052" in deploy_pi
    assert "T051 route ownership / API docs current-truth refresh is complete" in architecture
    assert "T052 stale packaging/root artifact cleanup is complete" in architecture
    assert "T051/T052 refreshed current-truth docs" in go_readme
    assert "go-primary-route-ownership-manifest.json" in index
    assert "T051 current-truth route ownership manifest" in index


def test_t052_stale_tracked_artifacts_are_absent_and_frontend_lockfile_remains():
    assert not (ROOT / "resources" / "python-embed.zip").exists()
    assert not (
        ROOT / "resources" / "wheels" / "pillow-12.0.0-cp312-cp312-win_amd64.whl"
    ).exists()
    assert not (ROOT / "package-lock.json").exists()
    assert (ROOT / "frontend" / "package-lock.json").exists()

    for path in (README_PATH, DOCS_README_PATH, CONTRIBUTING_PATH, DEPLOYMENT_PATH):
        text = _text(path)
        assert "embedded Python" in text or "Python zip" in text
        assert "Pillow" in text


def test_t051_t052_todo_closes_current_items_and_hands_off_to_t053():
    todo = _text(TODO_PATH)

    assert "T051/T052 Go primary current-truth refresh" in todo
    assert "目前未發現 tracked Reddit HTML 殘留" in todo
    assert "tests/test_go_primary_t051_t052_current_truth_cleanup.py" in todo
    assert _todo_row("T051").endswith("| Done |")
    assert _todo_row("T052").endswith("| Done |")
    assert _todo_row("T053").endswith("| Todo |")
    assert "下一個 active item 是 T053" in todo
