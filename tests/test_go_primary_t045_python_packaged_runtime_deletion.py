import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-python-packaged-runtime-deletion.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
DEPLOY_PI_PATH = ROOT / "DEPLOY-PI.md"
README_PATH = ROOT / "README.md"
DOCS_README_PATH = ROOT / "docs" / "README.md"
DEPLOYMENT_PATH = ROOT / "docs" / "DEPLOYMENT.md"
CONTRIBUTING_PATH = ROOT / "docs" / "CONTRIBUTING.md"
GO_README_PATH = ROOT / "go-shadow" / "README.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"
AGENTS_PATH = ROOT / "AGENTS.md"
CLAUDE_PATH = ROOT / "CLAUDE.md"
REQ_PATH = ROOT / "requirements.txt"
REQ_PI_PATH = ROOT / "requirements-pi.txt"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _text(path):
    return path.read_text(encoding="utf-8")


def test_t045_contract_records_packaged_runtime_deletion_without_source_deletion():
    contract = _contract()

    assert contract["task_id"] == "T045"
    assert contract["status"] == "completed_packaged_runtime_startup_deletion"
    assert contract["runtime_dependency_boundary"]["product_startup_requires_python"] is False
    assert contract["runtime_dependency_boundary"]["product_startup_requires_venv"] is False
    assert contract["runtime_dependency_boundary"]["product_startup_requires_flask"] is False
    assert contract["runtime_dependency_boundary"]["product_startup_requires_pyinstaller"] is False
    assert contract["removed_product_runtime_paths"]["embedded_python_runtime_dir"] == "python/"
    assert "app.py" in contract["retained_python_scope"]["backend_source"]
    assert "routes/" in contract["retained_python_scope"]["backend_source"]
    assert "requirements.txt" in contract["retained_python_scope"]["dependency_manifests"]
    assert "Delete Python backend source" in contract["not_done_by_t045"]
    assert contract["next_recommended_task"]["id"] == "T046"


def test_embedded_python_and_legacy_packaged_runtime_files_are_removed():
    removed_paths = [
        ROOT / "python",
        ROOT / "scripts" / "start_portable.bat",
        ROOT / "scripts" / "pack_portable.bat",
        ROOT / "scripts" / "build_release.py",
        ROOT / "deploy_v150.bat",
        ROOT / "v2-\u6253\u5305\u5230Prism_\u65e5\u5e38\u4f7f\u7528\u7248.bat",
    ]

    for path in removed_paths:
        assert not path.exists(), f"legacy packaged runtime path should be removed: {path}"

    for retained in [
        ROOT / "app.py",
        ROOT / "routes",
        ROOT / "migrations",
        REQ_PATH,
        REQ_PI_PATH,
    ]:
        assert retained.exists(), f"T045 should retain Python source/dev path until T053: {retained}"


def test_product_entrypoints_start_go_primary_without_python_packaged_dependencies():
    entrypoints = [
        ROOT / "scripts" / "start_go_primary.ps1",
        ROOT / "scripts" / "start.bat",
        ROOT / "start_v2.bat",
        ROOT / "scripts" / "install.bat",
        ROOT / "scripts" / "install.sh",
        ROOT / "scripts" / "pack.bat",
        ROOT / "deploy_to_pi.bat",
        ROOT / "deploy" / "raspberry_pi" / "setup.sh",
        ROOT / "deploy" / "raspberry_pi" / "Caddyfile",
    ]
    forbidden = [
        "python app.py",
        "python\\python.exe",
        "pip install",
        "requirements.txt",
        "requirements-pi.txt",
        "PyInstaller",
        "linux-venv",
        "Flask Backend",
    ]

    for path in entrypoints:
        body = _text(path)
        for token in forbidden:
            assert token.lower() not in body.lower(), f"{path} still contains {token!r}"

    starter = _text(ROOT / "scripts" / "start_go_primary.ps1")
    for token in [
        "prism-go-runtime.exe",
        "--enable-notes-write",
        "--enable-upload-write",
        "--enable-import-export",
        "--enable-server-system",
        "PRISM_GO_ALLOW_PROD_DB",
    ]:
        assert token in starter
    assert "PRISM_GO_ALLOW_PUBLIC_BIND" not in starter


def test_dependency_manifests_are_legacy_dev_test_only_not_product_startup():
    requirements = _text(REQ_PATH)
    requirements_pi = _text(REQ_PI_PATH)

    assert "Legacy Python source/dev/test only" in requirements
    assert "Legacy Python source/dev/test only" in requirements_pi
    assert "Flask==3.0.0" in requirements
    assert "python-magic-bin==0.4.14" in requirements
    assert "Flask==3.0.0" in requirements_pi
    assert "python-magic" in requirements_pi
    assert "Pillow" not in requirements
    assert "Pillow" not in requirements_pi


def test_t045_docs_mark_go_primary_product_startup_and_t046_source_followup():
    todo = _text(TODO_PATH)
    architecture = _text(ARCHITECTURE_PATH)
    schema = _text(SCHEMA_PATH)
    deploy_pi = _text(DEPLOY_PI_PATH)
    readme = _text(README_PATH)
    docs_readme = _text(DOCS_README_PATH)
    deployment = _text(DEPLOYMENT_PATH)
    contributing = _text(CONTRIBUTING_PATH)
    go_readme = _text(GO_README_PATH)
    go_report = _text(GO_REPORT_PATH)

    assert _text(AGENTS_PATH) == _text(CLAUDE_PATH)
    assert "go-primary-python-packaged-runtime-deletion.json" in todo
    assert "T045 Python packaged runtime deletion gate is complete" in architecture
    assert "Go T045" in schema
    assert "prism-go-primary.service" in deploy_pi
    assert "linux-venv" not in deploy_pi
    assert "ExecStart=/home/mask070924/prism/linux-venv/bin/python app.py" not in deploy_pi
    assert "Python source/dev/test only" in readme
    assert "Go primary" in docs_readme
    assert "Go primary deployment" in deployment
    assert "Python backend source remains legacy until T053" in contributing
    assert "Python Packaged Runtime Deletion" in go_readme
    assert "T045 removes the Python packaged runtime/startup path" in go_report

    t045_row = next(line for line in todo.splitlines() if line.startswith("| T045 "))
    t046_row = next(line for line in todo.splitlines() if line.startswith("| T046 "))
    t051_row = next(line for line in todo.splitlines() if line.startswith("| T051 "))
    t053_row = next(line for line in todo.splitlines() if line.startswith("| T053 "))
    assert t045_row.endswith("| Done |")
    assert t046_row.endswith("| Done |")
    assert t051_row.endswith("| Todo |")
    assert t053_row.endswith("| Todo |")
