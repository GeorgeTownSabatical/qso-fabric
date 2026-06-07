from __future__ import annotations

from services.quantum.fabric import FutureStateCandidate, Patch, ProjectionObject, QSOFabric, QuantumStateObject, RepairOperator, score_future_state_candidates


def test_projection_object_round_trips_json() -> None:
    projection = ProjectionObject(
        id="projection.best",
        projection_type="likely_case",
        source_fabric_id="fabric.current",
        projected_fabric_id="fabric.future",
        repair_ids=["repair.1"],
        horizon="next-session",
        expected_global_coherence=0.91,
        expected_obstruction_score=0.2,
        repair_history_refs=["history.1"],
        metadata={"stable": True},
    )

    restored = ProjectionObject.from_json_dict(projection.to_json_dict())

    assert restored == projection
    assert restored.to_json_dict() == projection.to_json_dict()


def test_future_state_candidate_round_trips_json() -> None:
    candidate = FutureStateCandidate(
        id="candidate.future",
        projection=_projection("projection.future", expected_global_coherence=0.88, expected_obstruction_score=0.3),
        supporting_repair_ids=["repair.1"],
        coherence_delta=0.12,
        obstruction_delta=0.7,
        repair_support=0.4,
        confidence=0.75,
        projection_cost=0.2,
        metadata={"kind": "repair-supported"},
    )

    restored = FutureStateCandidate.from_json_dict(candidate.to_json_dict())

    assert restored == candidate
    assert restored.to_json_dict() == candidate.to_json_dict()


def test_future_state_scoring_does_not_mutate_fabric() -> None:
    fabric = _fabric()
    before = fabric.to_json_dict()
    candidate = FutureStateCandidate(
        id="candidate.safe",
        projection=_projection("projection.safe", expected_global_coherence=0.8, expected_obstruction_score=0.4),
        supporting_repair_ids=[],
        coherence_delta=0.05,
        obstruction_delta=0.2,
        repair_support=0.1,
        confidence=0.6,
        projection_cost=0.1,
        metadata={},
    )

    report = score_future_state_candidates(fabric, [candidate])

    assert report["fabric_id"] == "fabric.projection"
    assert report["ranked_future_states"][0]["candidate_id"] == "candidate.safe"
    assert fabric.to_json_dict() == before


def test_future_state_ranking_prefers_repair_supported_low_obstruction_candidate() -> None:
    fabric = _fabric()
    repair = RepairOperator(
        id="repair.major",
        contradiction_ids=["contradiction.major"],
        operator_type="restriction_realign",
        affected_patch_ids=["patch.memory"],
        expected_obstruction_delta=1.1,
        continuity_role_impact=0.5,
        repair_cost=0.2,
        confidence=0.7,
        metadata={},
    )
    high_coherence_unsupported = FutureStateCandidate(
        id="candidate.high_coherence",
        projection=_projection("projection.high", expected_global_coherence=0.94, expected_obstruction_score=0.5),
        supporting_repair_ids=[],
        coherence_delta=0.1,
        obstruction_delta=0.1,
        repair_support=0.0,
        confidence=0.85,
        projection_cost=0.1,
        metadata={},
    )
    repair_supported = FutureStateCandidate(
        id="candidate.repair_supported",
        projection=_projection("projection.repair", expected_global_coherence=0.86, expected_obstruction_score=0.1, repair_ids=["repair.major"]),
        supporting_repair_ids=["repair.major"],
        coherence_delta=0.08,
        obstruction_delta=1.0,
        repair_support=0.2,
        confidence=0.65,
        projection_cost=0.2,
        metadata={},
    )

    report = score_future_state_candidates(
        fabric,
        [high_coherence_unsupported, repair_supported],
        repairs=[repair],
    )

    assert report["ranked_future_states"][0]["candidate_id"] == "candidate.repair_supported"
    assert report["ranked_future_states"][0]["expected_global_coherence"] < report["ranked_future_states"][1]["expected_global_coherence"]
    assert report["ranked_future_states"][0]["repair_support"] > report["ranked_future_states"][1]["repair_support"]


def _projection(
    projection_id: str,
    *,
    expected_global_coherence: float,
    expected_obstruction_score: float,
    repair_ids: list[str] | None = None,
) -> ProjectionObject:
    return ProjectionObject(
        id=projection_id,
        projection_type="likely_case",
        source_fabric_id="fabric.projection",
        projected_fabric_id=f"fabric.projection.{projection_id}",
        repair_ids=repair_ids or [],
        horizon="next-session",
        expected_global_coherence=expected_global_coherence,
        expected_obstruction_score=expected_obstruction_score,
        repair_history_refs=[],
        metadata={},
    )


def _fabric() -> QSOFabric:
    fabric = QSOFabric(id="fabric.projection")
    fabric.add_patch(
        Patch(
            id="patch.memory",
            domain="memory",
            basis=["|0>", "|1>"],
            state=QuantumStateObject(id="state.memory", vector=[1 + 0j, 0j]),
        )
    )
    return fabric
