from __future__ import annotations

from services.quantum.fabric import (
    Patch,
    QSOFabric,
    QuantumStateObject,
    StateBranch,
    StateMerge,
    StateReconciliation,
    StateSplit,
    StateTransform,
    TrustScore,
    score_reconciliation,
)


def test_state_algebra_primitives_round_trip_json() -> None:
    transform = StateTransform(
        id="transform.1",
        transform_type="merge",
        source_state_ids=["state.a", "state.b"],
        target_state_ids=["state.ab"],
        expected_coherence_delta=0.3,
        expected_obstruction_delta=0.4,
        confidence=0.8,
        cost=0.2,
        metadata={"operator": "descriptive"},
    )
    merge = StateMerge(id="merge.1", left_state_id="state.a", right_state_id="state.b", merged_state_id="state.ab", transform_id="transform.1")
    split = StateSplit(id="split.1", source_state_id="state.ab", split_state_ids=["state.a", "state.b"], transform_id="transform.2")
    branch = StateBranch(id="branch.1", source_state_id="state.a", branch_state_id="state.a.future", branch_type="projection", transform_id="transform.3")
    reconciliation = StateReconciliation(
        id="reconcile.1",
        transform_ids=["transform.1"],
        source_state_ids=["state.a", "state.b"],
        reconciled_state_id="state.ab",
        expected_coherence_delta=0.2,
        expected_obstruction_delta=0.5,
        trust_refs=["trust.score.state.ab"],
        confidence=0.7,
        cost=0.3,
        metadata={"safe": True},
    )

    assert StateTransform.from_json_dict(transform.to_json_dict()) == transform
    assert StateMerge.from_json_dict(merge.to_json_dict()) == merge
    assert StateSplit.from_json_dict(split.to_json_dict()) == split
    assert StateBranch.from_json_dict(branch.to_json_dict()) == branch
    assert StateReconciliation.from_json_dict(reconciliation.to_json_dict()) == reconciliation


def test_score_reconciliation_does_not_mutate_fabric() -> None:
    fabric = _fabric()
    before = fabric.to_json_dict()
    reconciliation = StateReconciliation(
        id="reconcile.safe",
        transform_ids=[],
        source_state_ids=["state.a"],
        reconciled_state_id="state.a.reconciled",
        expected_coherence_delta=0.1,
        expected_obstruction_delta=0.2,
        trust_refs=[],
        confidence=0.6,
        cost=0.1,
        metadata={},
    )

    report = score_reconciliation(fabric, [reconciliation])

    assert report["fabric_id"] == "fabric.algebra"
    assert report["ranked_reconciliations"][0]["reconciliation_id"] == "reconcile.safe"
    assert fabric.to_json_dict() == before


def test_score_reconciliation_prefers_supported_transform_over_raw_confidence() -> None:
    fabric = _fabric()
    transform = StateTransform(
        id="transform.strong",
        transform_type="reconcile",
        source_state_ids=["state.a", "state.b"],
        target_state_ids=["state.ab"],
        expected_coherence_delta=0.4,
        expected_obstruction_delta=0.8,
        confidence=0.6,
        cost=0.2,
        metadata={},
    )
    trust = TrustScore(
        id="trust.score.state.ab",
        target_ref="state.ab",
        score=0.9,
        confidence=0.8,
        evidence_ids=["trust.evidence.1"],
        vector_id="trust.vector.1",
        metadata={},
    )
    high_confidence_weak = StateReconciliation(
        id="reconcile.high_confidence",
        transform_ids=[],
        source_state_ids=["state.a"],
        reconciled_state_id="state.a.clean",
        expected_coherence_delta=0.1,
        expected_obstruction_delta=0.1,
        trust_refs=[],
        confidence=0.95,
        cost=0.1,
        metadata={},
    )
    lower_confidence_supported = StateReconciliation(
        id="reconcile.supported",
        transform_ids=["transform.strong"],
        source_state_ids=["state.a", "state.b"],
        reconciled_state_id="state.ab",
        expected_coherence_delta=0.2,
        expected_obstruction_delta=0.4,
        trust_refs=["trust.score.state.ab"],
        confidence=0.55,
        cost=0.2,
        metadata={},
    )

    report = score_reconciliation(
        fabric,
        [high_confidence_weak, lower_confidence_supported],
        transforms=[transform],
        trust_scores=[trust],
    )

    assert report["ranked_reconciliations"][0]["reconciliation_id"] == "reconcile.supported"
    assert report["ranked_reconciliations"][0]["confidence"] < report["ranked_reconciliations"][1]["confidence"]
    assert report["ranked_reconciliations"][0]["trust_support"] > report["ranked_reconciliations"][1]["trust_support"]


def _fabric() -> QSOFabric:
    fabric = QSOFabric(id="fabric.algebra")
    fabric.add_patch(
        Patch(
            id="patch.a",
            domain="memory",
            basis=["|0>", "|1>"],
            state=QuantumStateObject(id="state.a", vector=[1 + 0j, 0j]),
        )
    )
    fabric.add_patch(
        Patch(
            id="patch.b",
            domain="intent",
            basis=["|0>", "|1>"],
            state=QuantumStateObject(id="state.b", vector=[0j, 1 + 0j]),
        )
    )
    return fabric
