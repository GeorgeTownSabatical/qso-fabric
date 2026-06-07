from __future__ import annotations

from services.quantum.fabric import ContradictionObject, Patch, QSOFabric, QuantumStateObject, RepairOperator, score_repair_candidates


def test_contradiction_object_round_trips_json() -> None:
    contradiction = ContradictionObject(
        id="contradiction.1",
        mismatch_type="overlap_mismatch",
        affected_patch_ids=["patch.a", "patch.b"],
        affected_state_ids=["state.a", "state.b"],
        source_refs=["overlap.ab"],
        severity=0.8,
        obstruction_score=1.2,
        metadata={"note": "scored-not-fatal"},
    )

    restored = ContradictionObject.from_json_dict(contradiction.to_json_dict())

    assert restored == contradiction
    assert restored.to_json_dict() == contradiction.to_json_dict()


def test_repair_operator_round_trips_json() -> None:
    repair = RepairOperator(
        id="repair.1",
        contradiction_ids=["contradiction.1"],
        operator_type="restriction_reweight",
        affected_patch_ids=["patch.a"],
        expected_obstruction_delta=0.7,
        continuity_role_impact=0.4,
        repair_cost=0.2,
        confidence=0.6,
        metadata={"proposal": True},
    )

    restored = RepairOperator.from_json_dict(repair.to_json_dict())

    assert restored == repair
    assert restored.to_json_dict() == repair.to_json_dict()


def test_contradictions_are_scored_not_fatal() -> None:
    fabric = _fabric()
    contradiction = ContradictionObject(
        id="contradiction.high",
        mismatch_type="cohomology_obstruction",
        affected_patch_ids=["patch.memory"],
        affected_state_ids=["state.memory"],
        source_refs=["overlap.memory.intent"],
        severity=1.0,
        obstruction_score=1.8,
        metadata={},
    )
    repair = RepairOperator(
        id="repair.propose",
        contradiction_ids=["contradiction.high"],
        operator_type="metadata_reconcile",
        affected_patch_ids=["patch.memory"],
        expected_obstruction_delta=1.0,
        continuity_role_impact=0.5,
        repair_cost=0.2,
        confidence=0.7,
        metadata={},
    )

    report = score_repair_candidates(fabric, [contradiction], [repair])

    assert report["fabric_id"] == "fabric.repair"
    assert report["ranked_repairs"][0]["repair_id"] == "repair.propose"
    assert report["ranked_repairs"][0]["severity_coverage"] == 1.0


def test_repair_candidate_can_outrank_higher_confidence_candidate() -> None:
    fabric = _fabric()
    contradictions = [
        ContradictionObject(
            id="contradiction.low",
            mismatch_type="minor_mismatch",
            affected_patch_ids=["patch.intent"],
            affected_state_ids=["state.intent"],
            source_refs=["pair.low"],
            severity=0.2,
            obstruction_score=0.3,
            metadata={},
        ),
        ContradictionObject(
            id="contradiction.high",
            mismatch_type="major_mismatch",
            affected_patch_ids=["patch.memory"],
            affected_state_ids=["state.memory"],
            source_refs=["pair.high"],
            severity=0.8,
            obstruction_score=1.5,
            metadata={},
        ),
    ]
    high_confidence_small_repair = RepairOperator(
        id="repair.high_confidence",
        contradiction_ids=["contradiction.low"],
        operator_type="minor_relabel",
        affected_patch_ids=["patch.intent"],
        expected_obstruction_delta=0.2,
        continuity_role_impact=0.1,
        repair_cost=0.1,
        confidence=0.95,
        metadata={},
    )
    lower_confidence_better_repair = RepairOperator(
        id="repair.lower_confidence_better",
        contradiction_ids=["contradiction.high"],
        operator_type="restriction_realign",
        affected_patch_ids=["patch.memory"],
        expected_obstruction_delta=1.2,
        continuity_role_impact=0.4,
        repair_cost=0.2,
        confidence=0.55,
        metadata={},
    )

    report = score_repair_candidates(
        fabric,
        contradictions,
        [high_confidence_small_repair, lower_confidence_better_repair],
    )

    assert report["ranked_repairs"][0]["repair_id"] == "repair.lower_confidence_better"
    assert report["ranked_repairs"][0]["confidence"] < report["ranked_repairs"][1]["confidence"]
    assert report["ranked_repairs"][0]["severity_coverage"] > report["ranked_repairs"][1]["severity_coverage"]


def _fabric() -> QSOFabric:
    fabric = QSOFabric(id="fabric.repair")
    fabric.add_patch(
        Patch(
            id="patch.intent",
            domain="intent",
            basis=["|0>", "|1>"],
            state=QuantumStateObject(id="state.intent", vector=[1 + 0j, 0j]),
        )
    )
    fabric.add_patch(
        Patch(
            id="patch.memory",
            domain="memory",
            basis=["|0>", "|1>"],
            state=QuantumStateObject(id="state.memory", vector=[0j, 1 + 0j]),
        )
    )
    return fabric
