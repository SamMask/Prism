import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-python-package-deletion-closure.json"
D_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-live-cutover-rollback-proof.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
REQ_PATH = ROOT / "requirements.txt"
REQ_PI_PATH = ROOT / "requirements-pi.txt"
DEPLOY_PI_PATH = ROOT / "DEPLOY-PI.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_e_contract_closes_without_deleting_python_after_non_permanent_d_cutover():
    contract = _contract()
    d_contract = json.loads(D_CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["phase"] == "python-packaging-removal-E"
    assert contract["status"] == "completed_no_deletion_retained_python_package"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-go-live-cutover-rollback-proof.json"
    assert contract["no_auto_next_detail"] is True
    assert contract["no_e_next"] is True
    assert "allowed_next_step" not in contract
    assert "recommended_next_detail" not in contract
    assert d_contract["result"]["permanent_cutover"] is False
    assert contract["prerequisite_truth"]["D_permanent_cutover"] is False
    assert contract["prerequisite_truth"]["E_delete_precondition_met"] is False


def test_e_retains_python_package_files_and_dependency_manifests_truthfully():
    contract = _contract()
    requirements = REQ_PATH.read_text(encoding="utf-8")
    requirements_pi = REQ_PI_PATH.read_text(encoding="utf-8")
    deploy_pi = DEPLOY_PI_PATH.read_text(encoding="utf-8")

    assert contract["decision"]["delete_python_backend_package"] is False
    assert contract["decision"]["delete_python_runtime_dependencies"] is False
    assert contract["decision"]["delete_python_packaging_scripts"] is False
    assert "upload/delete/cleanup/import/export/server/migration-runner" in contract["decision"]["reason"]
    assert "Flask==3.0.0" in requirements
    assert "python-magic-bin==0.4.14" in requirements
    assert "Flask==3.0.0" in requirements_pi
    assert "python-magic" in requirements_pi
    assert "Pillow" not in requirements
    assert "Pillow" not in requirements_pi
    assert "ExecStart=/home/mask070924/prism/linux-venv/bin/python app.py" in deploy_pi
    assert "app.py" in contract["retained_python_runtime_files"]
    assert "routes/" in contract["retained_python_runtime_files"]
    assert "migrations/" in contract["retained_python_runtime_files"]


def test_e_blocks_package_deletion_and_runtime_mutation_scope():
    contract = _contract()

    assert "Python backend source" in contract["not_deleted_by_E"]
    assert "Flask requirements" in contract["not_deleted_by_E"]
    assert "Pi linux-venv install path" in contract["not_deleted_by_E"]
    assert "PyInstaller/build_release path" in contract["not_deleted_by_E"]
    assert "Implement missing Go upload/delete/cleanup/import/export/server/migration-runner surfaces" in contract["not_started_by_E"]
    assert "Rewrite prism.service to Go" in contract["not_started_by_E"]
    assert "Reload Caddy or systemd" in contract["not_started_by_E"]
    assert "Create E-next automatically" in contract["not_started_by_E"]


def test_docs_record_e_closure_without_e_next_or_false_python_removal_claim():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "A-E 已經跑完，但沒有達成「可以刪 Python」" in todo
    assert "D 不能永久 Go cutover 的直接原因" in todo
    assert "`/api/test`、`/api/categories`、`/api/tags`、`GET /api/notes`、`GET /api/system/migration-status`" in todo
    assert "如果把 Caddy 或 systemd 永久全量切到 Go，正式工作流會壞" in todo
    assert "E 的「完成」不是 Python package deletion 完成，而是 deletion decision 完成" in todo
    assert "E. Python package deletion — completed_no_deletion_retained_python_package" in todo
    assert "docs/contracts/phase23-python-package-deletion-closure.json" in todo
    assert "No E-next added" in todo
    assert "Phase 23 E Python package deletion is complete as `completed_no_deletion_retained_python_package`" in architecture
    assert "E did not delete Python backend source, Flask requirements" in architecture
    assert "`E. Python package deletion` is complete as `completed_no_deletion_retained_python_package`" in go_report
    assert "No E-next is added" in go_report

