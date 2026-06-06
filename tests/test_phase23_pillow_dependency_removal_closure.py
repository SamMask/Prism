import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
UPLOAD_URL_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-upload-url-local-candidate.json"
CLOSURE_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-pillow-dependency-removal-closure.json"
STABILIZATION_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-final-stabilization.json"
REQUIREMENTS_PATH = ROOT / "requirements.txt"
REQUIREMENTS_PI_PATH = ROOT / "requirements-pi.txt"
START_BAT_PATH = ROOT / "scripts" / "start.bat"
SMOKE_SCRIPT_PATH = ROOT / "scripts" / "smoke_go_local_artifact.ps1"
README_PATH = ROOT / "README.md"
UPLOAD_ROUTE_PATH = ROOT / "routes" / "upload.py"
IMPORT_ROUTE_PATH = ROOT / "routes" / "notes" / "import_.py"
SEQUENCE_UPLOAD_PATH = ROOT / "docs" / "SEQUENCE-UPLOAD.md"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_status_terms_and_concept_swap_rules_are_defined_in_todo():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "candidate_done" in todo
    assert "Go 已有候選實作或本機/copied-data 驗證" in todo
    assert "live_owner" in todo
    assert "正式 runtime / live route / packaged runtime 已由 Go 擁有" in todo
    assert "dependency_removed" in todo
    assert "正式封裝與正常執行路徑已不再需要該依賴" in todo
    assert "不得把 `candidate_done` 當成 `live_owner`" in todo
    assert "不得把 retained-Python stabilization 當成 `dependency_removed`" in todo
    assert "不得把 plan-only 文件當成交付完成" in todo
    assert "不得把 local/copied-data candidate 說成 live route owner" in todo
    assert "不得把 Go artifact build 成功說成 Python/Pillow removal 成功" in todo


def test_23_8_thumb_7_is_candidate_only_not_live_owner_or_dependency_removed():
    contract = _load(UPLOAD_URL_CONTRACT_PATH)
    semantics = contract["status_semantics"]
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert contract["phase"] == "23.8-thumb.7"
    assert semantics["candidate_done"] == "partial_yes"
    assert semantics["live_owner"] == "no"
    assert semantics["dependency_removed"] == "no"
    assert contract["runtime_changes"]["python_runtime_changed"] is False
    assert contract["runtime_changes"]["pillow_removed"] is False
    assert "狀態語義：`candidate_done: partial yes`；`live_owner: no`；`dependency_removed: no`" in todo
    assert "Status: `candidate_done: partial yes`; `live_owner: no`; `dependency_removed: no`." in architecture
    assert "Status: `candidate_done: partial yes`; `live_owner: no`; `dependency_removed: no`." in go_report


def test_pillow_dependency_removal_status_matches_actual_sources():
    closure = _load(CLOSURE_CONTRACT_PATH)
    evidence = closure["actual_source_evidence"]
    semantics = closure["status_semantics"]
    requirements = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    requirements_pi = REQUIREMENTS_PI_PATH.read_text(encoding="utf-8")
    start_bat = START_BAT_PATH.read_text(encoding="utf-8")
    upload_route = UPLOAD_ROUTE_PATH.read_text(encoding="utf-8")
    import_route = IMPORT_ROUTE_PATH.read_text(encoding="utf-8")
    sequence = SEQUENCE_UPLOAD_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")
    smoke_script = SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")

    assert closure["status"] == "completed"
    assert closure["not_a_new_plan_gate"] is True
    assert semantics["candidate_done"] == "yes_for_thumbnail_dependency_closure"
    assert semantics["live_owner"] == "retained_python_routes_delegate_thumbnail_generation_to_go_helper"
    assert semantics["dependency_removed"] == "yes_for_pillow"

    assert "Pillow" not in requirements
    assert "Pillow" not in requirements_pi
    assert "from PIL import Image" not in upload_route
    assert "from PIL import Image" not in import_route
    assert "PIL_AVAILABLE" not in upload_route
    assert "PIL_AVAILABLE" not in import_route
    assert "import PIL" not in start_bat
    assert "Pillow" not in sequence
    assert "Pillow（可選" not in readme
    assert "Python runtime 不依賴 Pillow" in readme
    assert "--thumbnail-input" in smoke_script
    assert "--thumbnail-output" in smoke_script
    assert "pillow_closure_thumb.webp" in smoke_script
    assert "RIFF" in smoke_script and "WEBP" in smoke_script

    assert evidence["requirements_txt_contains_pillow"] is False
    assert evidence["requirements_pi_txt_contains_pillow"] is False
    assert evidence["python_upload_imports_pil"] is False
    assert evidence["python_import_helper_imports_pil"] is False
    assert evidence["start_bat_imports_pil"] is False
    assert evidence["sequence_upload_mentions_pillow"] is False
    assert evidence["readme_mentions_pillow_runtime_dependency"] is False
    assert evidence["fresh_packaged_runtime_without_python_pillow_proven"] is True


def test_todo_records_pillow_closure_complete_and_keeps_next_work_b_to_e():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "23.8-thumb Go WebP thumbnail ownership / Pillow removal track — Pillow Dependency Removal Closed" in todo
    assert "- [x] **Pillow dependency removal closure**" in todo
    assert "- [x] **A. Pillow dependency removal closure**" in todo
    assert "`requirements.txt` 與 `requirements-pi.txt` 均不含 Pillow" in todo
    assert "fresh local packaged artifact 以 `--thumbnail-input` / `--thumbnail-output` 產生 `_thumb.webp`" in todo
    assert "`dependency_removed: yes for Pillow`" in todo
    assert "- [x] **B. Runtime ownership closure for Python removal — final retained-Python closure" in todo
    assert "不得新增 decision gate、route-by-route planning gate、`23.8-thumb.8/9/10`" in todo
    assert "23.8-thumb.8**" not in todo


def test_23_10_retained_python_is_not_dependency_removed_or_pure_go_packaging():
    stabilization = _load(STABILIZATION_CONTRACT_PATH)
    closure = stabilization["phase23_closure"]
    semantics = closure["status_semantics"]
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")
    next_steps = {step["id"]: step for step in stabilization["allowed_next_steps"]}

    assert closure["status"] == "closed_with_retained_python_normal_path"
    assert "not Python removal and not pure-Go packaging completion" in closure["summary"]
    assert semantics["live_owner"] == "python_remains_primary_normal_runtime_owner"
    assert semantics["dependency_removed"] == "no_for_python_yes_for_pillow_after_A_closure"
    assert "python-packaging-removal-roadmap-A-E" in next_steps
    assert "Do not add decision gates" in next_steps["python-packaging-removal-roadmap-A-E"]["scope"]
    assert "B runtime ownership closure is the active blocked item" in next_steps["python-packaging-removal-roadmap-A-E"]["scope"]

    assert "23.10 retained-Python stabilization 不是 Python removal" in todo
    assert "Pillow dependency removal 已在 A 完成" in todo
    assert "不是 Python removal and not pure-Go packaging completion" not in todo
    assert "retained-Python stabilization is not Python removal and not pure-Go packaging completion" in architecture
    assert "retained-Python stabilization is not Python removal and not pure-Go packaging completion" in go_report

