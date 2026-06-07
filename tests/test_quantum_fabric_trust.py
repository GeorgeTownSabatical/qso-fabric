from __future__ import annotations

from services.quantum.fabric import (
    FutureStateCandidate,
    Patch,
    ProjectionObject,
    QSOFabric,
    QuantumStateObject,
    RepairOperator,
    TrustEvidence,
    TrustPropagationRule,
    TrustScore,
    TrustVector,
    score_future_state_candidates,
    score_repair_candidates,
    score_trust,
)
from services.quantum.fabric.repair import ContradictionObject


def test_trust_primitives_round_trip_json() -> None:
    evidence = TrustEvidence(
        id="trust.evidence.1",
        source_ref="state.memory",
        target_ref="repair.1",
        evidence_type="repair_history",
        trust_delta=0.7,
        confidence=0.8,
        weight=1.2,
        metadata={"source": "test"},
    )
    vector = TrustVector(
        id="trust.vector.1",
        target_ref="repair.1",
        dimensions={"lineage": 0.8, "coherence": 0.7},
        evidence_ids=["trust.evidence.1"],
        metadata={"kind": "repair"},
    )
    rule = TrustPropagationRule(
        id="trust.rule.1",
        rule_type="lineage_inheritance",
        source_refs=["state.memory"],
        target_ref="repair.1",
        propagation_weight=0.6,
        decay=0.1,
        metadata={"bounded": True},
    )
    score = TrustScore(
        id="trust.score.1",
        target_ref="repair.1",
        score=0.75,
        confidence=0.8,
        evidence_ids=["trust.evidence.1"],
        vector_id="trust.vector.1",
        metadata={"rank": 1},
    )

    assert TrustEvidence.from_json_dict(evidence.to_json_dict()) == evidence
    assert TrustVector.from_json_dict(vector.to_json_dict()) == vector
    assert TrustPropagationRule.from_json_dict(rule.to_json_dict()) == rule
    assert TrustScore.from_json_dict(score.to_json_dict()) == score


def test_score_trust_ranks_targets_deterministically() -> None:
    fabric = _fabric()
    vectors = [
        TrustVector(id="vector.low", target_ref="repair.low", dimensions={"lineage": 0.2, "coherence": 0.3}, evidence_ids=[]),
        TrustVector(id="vector.high", target_ref="repair.high", dimensions={"lineage": 0.8, "coherence": 0.9}, evidence_ids=["e.high"]),
    ]
    evidence = [
        TrustEvidence(id="e.low", source_ref="state.memory", target_ref="repair.low", evidence_type="manual", trust_delta=0.1, confidence=0.9),
        TrustEvidence(id="e.high", source_ref="state.memory", target_ref="repair.high", evidence_type="history", trust_delta=0.6, confidence=0.8),
    ]

    report = score_trust(fabric, vectors, evidence)

    assert report["fabric_id"] == "fabric.trust"
    assert report["ranked_trust"][0]["target_ref"] == "repair.high"
    assert report["ranked_trust"][0]["score"] > report["ranked_trust"][1]["score"]


def test_trust_can_feed_repair_scoring_as_input_evidence() -> None:
    fabric = _fabric()
    contradiction = ContradictionObject(
        id="contradiction.1",
        mismatch_type="trust_weighted_obstruction",
        affected_patch_ids=["patch.memory"],
        affected_state_ids=["state.memory"],
        source_refs=["overlap.1"],
        severity=1.0,
        obstruction_score=1.0,
        metadata={},
    )
    trust_report = score_trust(
        fabric,
        [TrustVector(id="vector.repair", target_ref="repair.trusted", dimensions={"lineage": 0.9}, evidence_ids=["e.repair"])],
        [TrustEvidence(id="e.repair", source_ref="state.memory", target_ref="repair.trusted", evidence_type="repair_history", trust_delta=0.8, confidence=0.9)],
    )
    trust_confidence = trust_report["ranked_trust"][0]["confidence"]
    trusted_repair = RepairOperator(
        id="repair.trusted",
        contradiction_ids=["contradiction.1"],
        operator_type="trusted_realign",
        affected_patch_ids=["patch.memory"],
        expected_obstruction_delta=0.8,
        continuity_role_impact=0.4,
        repair_cost=0.2,
        confidence=trust_confidence,
        metadata={"trust_score_ref": "trust.score.repair.trusted"},
    )

    report = score_repair_candidates(fabric, [contradiction], [trusted_repair])

    assert report["ranked_repairs"][0]["repair_id"] == "repair.trusted"
    assert report["ranked_repairs"][0]["confidence"] == trust_confidence


def test_trust_can_feed_projection_support_as_input_evidence() -> None:
    fabric = _fabric()
    repair = RepairOperator(
        id="repair.projection",
        contradiction_ids=["contradiction.1"],
        operator_type="projection_support",
        affected_patch_ids=["patch.memory"],
        expected_obstruction_delta=0.9,
        continuity_role_impact=0.5,
        repair_cost=0.2,
        confidence=0.7,
        metadata={},
    )
    trust_report = score_trust(
        fabric,
        [TrustVector(id="vector.projection", target_ref="projection.future", dimensions={"lineage": 0.8, "repair": 0.9}, evidence_ids=["e.projection"])],
        [TrustEvidence(id="e.projection", source_ref="repair.projection", target_ref="projection.future", evidence_type="projection_history", trust_delta=0.7, confidence=0.8)],
    )
    projection_support = trust_report["ranked_trust"][0]["score"]
    candidate = FutureStateCandidate(
        id="candidate.trusted",
        projection=ProjectionObject(
            id="projection.future",
            projection_type="likely_case",
            source_fabric_id="fabric.trust",
            projected_fabric_id="fabric.future",
            repair_ids=["repair.projection"],
            horizon="next-session",
            expected_global_coherence=0.8,
            expected_obstruction_score=0.2,
            repair_history_refs=["trust.score.projection.future"],
            metadata={},
        ),
        supporting_repair_ids=["repair.projection"],
        coherence_delta=0.1,
        obstruction_delta=0.6,
        repair_support=projection_support,
        confidence=0.7,
        projection_cost=0.2,
        metadata={"trust_score_ref": "trust.score.projection.future"},
    )

    report = score_future_state_candidates(fabric, [candidate], repairs=[repair])

    assert report["ranked_future_states"][0]["candidate_id"] == "candidate.trusted"
    assert report["ranked_future_states"][0]["repair_support"] > projection_support


def _fabric() -> QSOFabric:
    fabric = QSOFabric(id="fabric.trust")
    fabric.add_patch(
        Patch(
            id="patch.memory",
            domain="memory",
            basis=["|0>", "|1>"],
            state=QuantumStateObject(id="state.memory", vector=[1 + 0j, 0j]),
        )
    )
    return fabric
