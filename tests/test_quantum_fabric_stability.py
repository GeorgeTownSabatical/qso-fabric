from __future__ import annotations

from services.quantum.fabric import (
    CorrelationObject,
    FutureStateCandidate,
    ManifoldStabilityScore,
    ObservationObject,
    Patch,
    ProjectionObject,
    QSOFabric,
    QuantumStateObject,
    RepairOperator,
    StabilitySignal,
    StabilityThreshold,
    TrustScore,
    score_manifold_stability,
)


def test_stability_primitives_round_trip_json() -> None:
    signal = StabilitySignal(
        id="stability.signal.1",
        region_ref="patch.a",
        signal_type="coherence",
        magnitude=0.8,
        confidence=0.7,
        source_refs=["observation.1"],
        metadata={"kind": "descriptive"},
    )
    threshold = StabilityThreshold(
        id="stability.threshold.1",
        region_ref="patch.a",
        minimum_score=0.5,
        warning_score=0.7,
        metadata={"gate": "future"},
    )
    score = ManifoldStabilityScore(
        id="stability.score.patch.a",
        region_ref="patch.a",
        score=0.75,
        stable=True,
        warning=False,
        threshold_id="stability.threshold.1",
        confidence=0.7,
        metadata={"rank": 1},
    )

    assert StabilitySignal.from_json_dict(signal.to_json_dict()) == signal
    assert StabilityThreshold.from_json_dict(threshold.to_json_dict()) == threshold
    assert ManifoldStabilityScore.from_json_dict(score.to_json_dict()) == score


def test_score_manifold_stability_ranks_deterministically() -> None:
    fabric = _fabric()
    signals = [
        StabilitySignal(id="signal.b", region_ref="patch.b", signal_type="coherence", magnitude=0.5, confidence=0.5, source_refs=[], metadata={}),
        StabilitySignal(id="signal.a", region_ref="patch.a", signal_type="coherence", magnitude=0.9, confidence=0.9, source_refs=[], metadata={}),
    ]
    thresholds = [
        StabilityThreshold(id="threshold.a", region_ref="patch.a", minimum_score=0.2, warning_score=0.4),
        StabilityThreshold(id="threshold.b", region_ref="patch.b", minimum_score=0.2, warning_score=0.4),
    ]

    report = score_manifold_stability(fabric, signals, thresholds)

    assert [item["region_ref"] for item in report["ranked_stability"]] == ["patch.a", "patch.b"]


def test_unstable_manifold_scores_below_threshold() -> None:
    fabric = _fabric()
    signals = [
        StabilitySignal(id="signal.entropy", region_ref="patch.a", signal_type="entropy", magnitude=0.9, confidence=0.9, source_refs=["observation.entropy"], metadata={}),
    ]
    thresholds = [
        StabilityThreshold(id="threshold.a", region_ref="patch.a", minimum_score=0.6, warning_score=0.75),
    ]

    report = score_manifold_stability(fabric, signals, thresholds)
    score = report["ranked_stability"][0]

    assert score["region_ref"] == "patch.a"
    assert score["stable"] is False
    assert score["warning"] is True
    assert score["score"] < 0.6


def test_correlation_trust_observation_repair_projection_support_affects_stability() -> None:
    fabric = _fabric()
    signals = [
        StabilitySignal(id="signal.supported", region_ref="patch.a", signal_type="coherence", magnitude=0.3, confidence=0.7, source_refs=["observation.a"], metadata={}),
        StabilitySignal(id="signal.raw", region_ref="patch.b", signal_type="coherence", magnitude=0.4, confidence=0.7, source_refs=["observation.b"], metadata={}),
    ]
    thresholds = [
        StabilityThreshold(id="threshold.a", region_ref="patch.a", minimum_score=0.2, warning_score=0.4),
        StabilityThreshold(id="threshold.b", region_ref="patch.b", minimum_score=0.2, warning_score=0.4),
    ]
    correlations = [
        CorrelationObject(id="correlation.a", correlation_type="support", left_ref="patch.a", right_ref="patch.c", strength=0.8, confidence=0.8, source_refs=["source.1"], metadata={}),
    ]
    observations = [
        ObservationObject(id="observation.a", observer_ref="agent.local", target_ref="patch.a", observation_type="coherence", signal="stable", magnitude=0.9, confidence=0.8, source_refs=["sensor.1"], metadata={}),
    ]
    trust_scores = [
        TrustScore(id="trust.score.patch.a", target_ref="patch.a", score=0.9, confidence=0.8, evidence_ids=["trust.evidence.1"], vector_id="trust.vector.1", metadata={}),
    ]
    repairs = [
        RepairOperator(id="repair.a", contradiction_ids=["contradiction.a"], operator_type="stabilize", affected_patch_ids=["patch.a"], expected_obstruction_delta=0.7, continuity_role_impact=0.4, repair_cost=0.2, confidence=0.8, metadata={}),
    ]
    projections = [
        FutureStateCandidate(
            id="future.a",
            projection=ProjectionObject(
                id="projection.a",
                projection_type="likely_case",
                source_fabric_id="patch.a",
                projected_fabric_id="patch.future",
                repair_ids=["repair.a"],
                horizon="next",
                expected_global_coherence=0.8,
                expected_obstruction_score=0.2,
                repair_history_refs=[],
                metadata={},
            ),
            supporting_repair_ids=["repair.a"],
            coherence_delta=0.2,
            obstruction_delta=0.5,
            repair_support=0.4,
            confidence=0.8,
            projection_cost=0.2,
            metadata={},
        ),
    ]

    report = score_manifold_stability(
        fabric,
        signals,
        thresholds,
        correlations=correlations,
        observations=observations,
        trust_scores=trust_scores,
        repair_candidates=repairs,
        projection_candidates=projections,
    )

    by_region = {item["region_ref"]: item for item in report["ranked_stability"]}
    assert report["ranked_stability"][0]["region_ref"] == "patch.a"
    assert by_region["patch.a"]["metadata"]["trust_support"] > by_region["patch.b"]["metadata"]["trust_support"]
    assert by_region["patch.a"]["metadata"]["correlation_support"] > by_region["patch.b"]["metadata"]["correlation_support"]
    assert by_region["patch.a"]["metadata"]["observation_support"] > by_region["patch.b"]["metadata"]["observation_support"]


def test_score_manifold_stability_does_not_mutate_fabric() -> None:
    fabric = _fabric()
    before = fabric.to_json_dict()
    signals = [
        StabilitySignal(id="signal.safe", region_ref="patch.a", signal_type="coherence", magnitude=0.8, confidence=0.8, source_refs=[], metadata={}),
    ]
    thresholds = [
        StabilityThreshold(id="threshold.a", region_ref="patch.a", minimum_score=0.2, warning_score=0.4),
    ]

    report = score_manifold_stability(fabric, signals, thresholds)

    assert report["fabric_id"] == "fabric.stability"
    assert fabric.to_json_dict() == before


def _fabric() -> QSOFabric:
    fabric = QSOFabric(id="fabric.stability")
    for state_id, patch_id, domain, vector in (
        ("state.a", "patch.a", "memory", [1 + 0j, 0j]),
        ("state.b", "patch.b", "intent", [0j, 1 + 0j]),
        ("state.c", "patch.c", "projection", [1 + 0j, 1 + 0j]),
    ):
        fabric.add_patch(
            Patch(
                id=patch_id,
                domain=domain,
                basis=["|0>", "|1>"],
                state=QuantumStateObject(id=state_id, vector=vector),
            )
        )
    return fabric
