from __future__ import annotations

from services.quantum.fabric import (
    CorrelationCluster,
    CorrelationMetric,
    CorrelationObject,
    ObservationObject,
    Patch,
    QSOFabric,
    QuantumStateObject,
    TrustScore,
    score_correlations,
)


def test_correlation_primitives_round_trip_json() -> None:
    correlation = CorrelationObject(
        id="correlation.1",
        correlation_type="shared_observation",
        left_ref="state.a",
        right_ref="state.b",
        strength=0.7,
        confidence=0.8,
        source_refs=["observation.1"],
        metadata={"kind": "descriptive"},
    )
    metric = CorrelationMetric(
        id="metric.1",
        correlation_id="correlation.1",
        metric_type="cosine_like",
        value=0.7,
        confidence=0.8,
        source_refs=["observation.1"],
        metadata={"stable": True},
    )
    cluster = CorrelationCluster(
        id="cluster.1",
        correlation_ids=["correlation.1"],
        member_refs=["state.a", "state.b"],
        centroid_ref="state.a",
        cohesion_score=0.9,
        metadata={"members": 2},
    )

    assert CorrelationObject.from_json_dict(correlation.to_json_dict()) == correlation
    assert CorrelationMetric.from_json_dict(metric.to_json_dict()) == metric
    assert CorrelationCluster.from_json_dict(cluster.to_json_dict()) == cluster


def test_score_correlations_ranks_deterministically_with_tie_break() -> None:
    fabric = _fabric()
    correlations = [
        CorrelationObject(
            id="correlation.b",
            correlation_type="tie",
            left_ref="state.a",
            right_ref="state.b",
            strength=0.5,
            confidence=0.5,
            source_refs=["source.1"],
            metadata={},
        ),
        CorrelationObject(
            id="correlation.a",
            correlation_type="tie",
            left_ref="state.a",
            right_ref="state.b",
            strength=0.5,
            confidence=0.5,
            source_refs=["source.1"],
            metadata={},
        ),
    ]

    report = score_correlations(fabric, correlations)

    assert [item["correlation_id"] for item in report["ranked_correlations"]] == ["correlation.a", "correlation.b"]


def test_score_correlations_uses_observations_and_trust_as_input_evidence() -> None:
    fabric = _fabric()
    correlations = [
        CorrelationObject(
            id="correlation.weak_raw",
            correlation_type="raw",
            left_ref="state.a",
            right_ref="state.b",
            strength=0.7,
            confidence=0.7,
            source_refs=["source.1"],
            metadata={},
        ),
        CorrelationObject(
            id="correlation.supported",
            correlation_type="supported",
            left_ref="state.a",
            right_ref="state.c",
            strength=0.5,
            confidence=0.6,
            source_refs=["source.2", "source.3"],
            metadata={},
        ),
    ]
    observations = [
        ObservationObject(
            id="observation.c",
            observer_ref="agent.local",
            target_ref="state.c",
            observation_type="coherence",
            signal="shared_context",
            magnitude=0.9,
            confidence=0.9,
            source_refs=["sensor.1"],
            metadata={},
        )
    ]
    trust_scores = [
        TrustScore(
            id="trust.score.state.c",
            target_ref="state.c",
            score=0.8,
            confidence=0.9,
            evidence_ids=["trust.evidence.1"],
            vector_id="trust.vector.1",
            metadata={},
        )
    ]

    report = score_correlations(fabric, correlations, observations=observations, trust_scores=trust_scores)

    assert report["ranked_correlations"][0]["correlation_id"] == "correlation.supported"
    assert report["ranked_correlations"][0]["trust_support"] > report["ranked_correlations"][1]["trust_support"]
    assert report["ranked_correlations"][0]["observation_support"] > report["ranked_correlations"][1]["observation_support"]


def test_score_correlations_does_not_mutate_fabric() -> None:
    fabric = _fabric()
    before = fabric.to_json_dict()
    correlation = CorrelationObject(
        id="correlation.safe",
        correlation_type="no_mutation",
        left_ref="state.a",
        right_ref="state.b",
        strength=0.8,
        confidence=0.7,
        source_refs=["source.1"],
        metadata={},
    )

    report = score_correlations(fabric, [correlation])

    assert report["fabric_id"] == "fabric.correlation"
    assert report["ranked_correlations"][0]["correlation_id"] == "correlation.safe"
    assert fabric.to_json_dict() == before


def _fabric() -> QSOFabric:
    fabric = QSOFabric(id="fabric.correlation")
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
