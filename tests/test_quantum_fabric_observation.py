from __future__ import annotations

from services.quantum.fabric import (
    ObservationFrame,
    ObservationObject,
    ObservationScore,
    Patch,
    QSOFabric,
    QuantumStateObject,
    TrustScore,
    score_observations,
)


def test_observation_primitives_round_trip_json() -> None:
    observation = ObservationObject(
        id="observation.1",
        observer_ref="agent.local",
        target_ref="state.memory",
        observation_type="state_signal",
        signal="coherence_probe",
        magnitude=0.8,
        confidence=0.7,
        source_refs=["sensor.1"],
        metadata={"note": "descriptive"},
    )
    frame = ObservationFrame(
        id="frame.1",
        fabric_id="fabric.observation",
        observation_ids=["observation.1"],
        horizon="now",
        context_refs=["context.1"],
        metadata={"scope": "test"},
    )
    score = ObservationScore(
        id="observation.score.1",
        observation_id="observation.1",
        target_ref="state.memory",
        score=0.75,
        relevance=0.56,
        confidence=0.7,
        trust_support=0.4,
        metadata={"rank": 1},
    )

    assert ObservationObject.from_json_dict(observation.to_json_dict()) == observation
    assert ObservationFrame.from_json_dict(frame.to_json_dict()) == frame
    assert ObservationScore.from_json_dict(score.to_json_dict()) == score


def test_score_observations_ranks_deterministically_with_trust_support() -> None:
    fabric = _fabric()
    observations = [
        ObservationObject(
            id="observation.low",
            observer_ref="agent.local",
            target_ref="state.low",
            observation_type="memory",
            signal="weak",
            magnitude=0.3,
            confidence=0.9,
            source_refs=["source.1"],
            metadata={},
        ),
        ObservationObject(
            id="observation.high",
            observer_ref="agent.local",
            target_ref="state.high",
            observation_type="memory",
            signal="trusted",
            magnitude=0.6,
            confidence=0.7,
            source_refs=["source.1", "source.2"],
            metadata={},
        ),
    ]
    trust_scores = [
        TrustScore(
            id="trust.score.state.high",
            target_ref="state.high",
            score=0.9,
            confidence=0.8,
            evidence_ids=["trust.evidence.1"],
            vector_id="trust.vector.1",
            metadata={},
        )
    ]

    report = score_observations(fabric, observations, trust_scores=trust_scores)

    assert report["fabric_id"] == "fabric.observation"
    assert report["ranked_observations"][0]["observation_id"] == "observation.high"
    assert report["ranked_observations"][0]["trust_support"] > report["ranked_observations"][1]["trust_support"]


def test_score_observations_frame_filters_observations_without_mutating_fabric() -> None:
    fabric = _fabric()
    before = fabric.to_json_dict()
    observations = [
        ObservationObject(
            id="observation.included",
            observer_ref="agent.local",
            target_ref="state.memory",
            observation_type="intent",
            signal="included",
            magnitude=0.5,
            confidence=0.7,
            source_refs=["source.1"],
            metadata={},
        ),
        ObservationObject(
            id="observation.excluded",
            observer_ref="agent.local",
            target_ref="state.memory",
            observation_type="intent",
            signal="excluded",
            magnitude=1.0,
            confidence=1.0,
            source_refs=["source.2"],
            metadata={},
        ),
    ]
    frame = ObservationFrame(
        id="frame.now",
        fabric_id="fabric.observation",
        observation_ids=["observation.included"],
        horizon="now",
        context_refs=[],
        metadata={},
    )

    report = score_observations(fabric, observations, frame=frame)

    assert report["frame_id"] == "frame.now"
    assert [item["observation_id"] for item in report["ranked_observations"]] == ["observation.included"]
    assert fabric.to_json_dict() == before


def _fabric() -> QSOFabric:
    fabric = QSOFabric(id="fabric.observation")
    fabric.add_patch(
        Patch(
            id="patch.memory",
            domain="memory",
            basis=["|0>", "|1>"],
            state=QuantumStateObject(id="state.memory", vector=[1 + 0j, 0j]),
        )
    )
    return fabric
