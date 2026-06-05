import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-webp-encoder-dependency-decision.json"
SOURCE_PLAN_PATH = ROOT / "docs" / "contracts" / "phase23-go-local-packaging-thumbnail-plan.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
REQUIREMENTS_PATH = ROOT / "requirements.txt"
UPLOAD_ROUTE_PATH = ROOT / "routes" / "upload.py"
IMPORT_ROUTE_PATH = ROOT / "routes" / "notes" / "import_.py"
GO_MOD_PATH = ROOT / "go-shadow" / "go.mod"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_23_8_thumb_1_is_plan_only_and_keeps_live_thumbnail_owner_unchanged():
    contract = _contract()
    runtime = contract["runtime_changes"]
    blocked = set(contract["not_authorized_by_23_8_thumb_1"])

    assert contract["phase"] == "23.8-thumb.1"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["scope_type"] == "plan_only_dependency_decision"
    assert all(changed is False for changed in runtime.values())
    assert contract["fallback_policy"]["live_owner"] == "Python/Pillow remains the thumbnail owner"
    assert "Add github.com/skrashevich/go-webp to go-shadow/go.mod" in blocked
    assert "Remove Pillow from requirements.txt" in blocked
    assert "Change routes/upload.py or routes/notes/import_.py" in blocked
    assert "Deploy to Pi" in blocked


def test_current_python_thumbnail_contract_matches_23_8_1_source_plan():
    contract = _contract()
    source_plan = json.loads(SOURCE_PLAN_PATH.read_text(encoding="utf-8"))
    current = contract["current_python_thumbnail_contract"]
    source_current = source_plan["thumbnail_webp_plan"]["current_contract"]

    assert current["owner"] == source_plan["thumbnail_webp_plan"]["current_owner"]
    assert current["routes_and_helpers"] == source_current["routes"]
    assert current["input_mimes"] == source_current["input_mimes"]
    assert current["output_convention"] == source_current["output_convention"]
    assert current["max_width_px"] == source_current["max_width_px"] == 500
    assert current["quality"] == source_current["quality"] == 80
    assert "_thumb.webp" in current["cleanup_contract"]


def test_candidate_matrix_rejects_decode_only_or_packaging_risky_options():
    candidates = {item["module"]: item for item in _contract()["candidate_evaluation"]}

    x_image = candidates["golang.org/x/image/webp"]
    chai = candidates["github.com/chai2010/webp"]
    kolesa = candidates["github.com/kolesa-team/go-webp"]
    nativewebp = candidates["github.com/HugoSmits86/nativewebp"]

    assert x_image["encode_support"] is False
    assert x_image["decision"] == "rejected_decode_only"
    assert "decode" in x_image["reason"].lower()
    assert chai["encode_support"] is True
    assert chai["decision"] == "rejected_for_first_spike"
    assert "toolchain" in chai["reason"]
    assert kolesa["encode_support"] is True
    assert kolesa["cgo_status"] == "cgo_libwebp_binding"
    assert kolesa["decision"] == "rejected_for_first_spike"
    assert nativewebp["cgo_status"] == "pure_go"
    assert nativewebp["decision"] == "fallback_or_secondary_spike_only"
    assert "lossless" in nativewebp["reason"]


def test_selected_candidate_is_pure_go_spike_only_with_build_probe_evidence():
    contract = _contract()
    selected = contract["selected_candidate"]
    probe = contract["build_probe"]
    results = probe["results"]

    assert contract["decision"] == "select_skrashevich_go_webp_for_spike_only"
    assert selected["module"] == "github.com/skrashevich/go-webp"
    assert selected["version_probed"] == "v0.1.0"
    assert selected["selection_scope"].endswith("not a production dependency in this gate")
    assert "quality=80" in next(
        item["reason"]
        for item in contract["candidate_evaluation"]
        if item["module"] == "github.com/skrashevich/go-webp"
    )
    assert probe["module_under_probe"] == "github.com/skrashevich/go-webp v0.1.0"
    assert results["go_run_windows"] == "passed"
    assert results["windows_build"] == "passed"
    assert results["windows_artifact_bytes"] > 0
    assert results["linux_arm64_cgo0_build"] == "passed"
    assert results["linux_arm64_artifact_bytes"] > 0
    assert "production upload/import parity fixtures are still required" in probe["limits"][0]


def test_pillow_and_go_runtime_dependencies_are_not_changed_by_decision_gate():
    contract = _contract()
    requirements = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    upload_route = UPLOAD_ROUTE_PATH.read_text(encoding="utf-8")
    import_route = IMPORT_ROUTE_PATH.read_text(encoding="utf-8")

    assert contract["runtime_changes"]["go_mod_changed"] is False
    assert contract["runtime_changes"]["go_webp_encoder_added"] is False
    assert "Pillow" not in requirements
    assert "from PIL import Image" not in upload_route
    assert "from PIL import Image" not in import_route
    assert "generate_webp_thumbnail" in upload_route
    assert "generate_webp_thumbnail" in import_route
    assert "_thumb.webp" in upload_route
    assert "thumbnail_name" in import_route


def test_docs_record_23_8_thumb_1_completion_and_23_8_thumb_2_next_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.8-thumb Go WebP thumbnail ownership / Pillow removal track" in todo
    assert "23.8-thumb.1** WebP encoder dependency decision" in todo
    assert "github.com/skrashevich/go-webp" in todo
    assert "23.8-thumb.2** Thumbnail parity fixtures" in todo
    assert "Phase 23.8-thumb.1 Go WebP encoder dependency decision is complete as plan-only" in architecture
    assert "23.8-thumb.2 Thumbnail parity fixtures" in architecture
    assert "`23.8-thumb.1 Go WebP encoder dependency decision` is complete as plan-only" in go_report
    assert "`23.8-thumb.2 Thumbnail parity fixtures`" in go_report
