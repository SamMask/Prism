import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "contracts" / "phase19-go-cutover-readiness-audit.json"
ROUTING_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase19-go-read-routing-proof.json"


def _audit():
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_phase19_4_is_audit_only_and_does_not_authorize_cutover():
    audit = _audit()

    assert audit["phase"] == "19.4"
    assert audit["decision"] == "ready_for_separate_readonly_service_plan"
    assert audit["decision_scope"] == "audit_only"
    assert audit["runtime_change"] is False

    not_authorized = " ".join(audit["not_authorized_by_19_4"]).lower()
    assert "replacing prism.service" in not_authorized
    assert "writing to production knowledge.db" in not_authorized
    assert "running migrations from go" in not_authorized
    assert "removing python runtime" in not_authorized


def test_phase19_4_preserves_known_cutover_gaps():
    audit = _audit()
    gaps = " ".join(audit["blocking_gaps_before_any_cutover"]).lower()

    assert "no production service-level cutover plan exists" in gaps
    assert "no live pi service replacement" in gaps
    assert "no long-running read-routing soak" in gaps
    assert "go still does not own post / put / delete" in gaps
    assert "python remains required" in gaps


def test_phase19_4_evidence_covers_prior_phase_gates():
    audit = _audit()
    evidence = audit["evidence"]

    for key in (
        "phase19_0_runtime_packaging",
        "phase19_1_real_data_canary",
        "phase19_2_promotion_gate",
        "phase19_3_read_routing_proof",
    ):
        assert key in evidence
        assert evidence[key]

    phase19_3 = " ".join(evidence["phase19_3_read_routing_proof"]).lower()
    assert "defaults off" in phase19_3
    assert "fail open to python" in phase19_3
    assert "x-prism-go-read-routing: hit" in phase19_3


def test_phase19_4_next_step_is_separate_user_approved_plan():
    audit = _audit()
    next_step = audit["allowed_next_step"]

    assert next_step["id"] == "19.5"
    assert next_step["requires_user_approval_before_execution"] is True
    assert "read-only service-level cutover" in next_step["title"].lower()

    forbidden = " ".join(next_step["must_not_include"]).lower()
    assert "post / put / delete" in forbidden
    assert "go migrations" in forbidden
    assert "production db writes" in forbidden
    assert "python backend removal" in forbidden


def test_phase19_3_contract_points_to_19_4_audit_boundary():
    contract = json.loads(ROUTING_CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["next_phase"]["id"] == "19.4"
    assert "Cutover Readiness Audit" in contract["next_phase"]["title"]
    assert "production cutover" in contract["next_phase"]["must_not_include"]
