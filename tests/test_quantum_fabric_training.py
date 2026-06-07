from __future__ import annotations

from services.quantum.fabric import (
    FutureStateCandidate,
    ManifoldStabilityScore,
    ModelCorrection,
    ModelObservation,
    Patch,
    ProjectionObject,
    QSOFabric,
    QuantumStateObject,
    RepairOperator,
    TrainingExample,
    TrainingExampleScore,
    TrainingSignal,
    TrainingTrace,
    TrustScore,
    score_training_examples,
)


def test_training_primitives_round_trip_json() -> None:
    observation = ModelObservation(
        id="model.observation.1",
        model_ref="model.local",
        input_ref="prompt.1",
        output_ref="response.1",
        observation_type="contradiction",
        magnitude=0.8,
        confidence=0.7,
        source_refs=["eval.1"],
        metadata={"kind": "repairable"},
    )
    correction = ModelCorrection(
        id="model.correction.1",
        observation_ids=["model.observation.1"],
        correction_type="factual_repair",
        target_ref="response.1",
        corrected_output="Corrected answer.",
        improvement_score=0.9,
        confidence=0.8,
        source_refs=["human.1"],
        metadata={"style": "concise"},
    )
    signal = TrainingSignal(
        id="training.signal.1",
        example_id="training.example.1",
        signal_type="useful_repair",
        magnitude=0.85,
        confidence=0.75,
        source_refs=["repair.1"],
        metadata={"dataset": "sft"},
    )
    example = TrainingExample(
        id="training.example.1",
        input_text="Question?",
        output_text="Answer.",
        correction_id="model.correction.1",
        observation_ids=["model.observation.1"],
        trust_refs=["trust.score.1"],
        stability_refs=["stability.score.1"],
        repair_refs=["repair.1"],
        projection_refs=["future.1"],
        provenance_refs=["source.1"],
        metadata={"dataset_kind": "sft"},
    )
    trace = TrainingTrace(
        id="training.trace.1",
        fabric_id="fabric.training",
        model_ref="model.local",
        example_ids=["training.example.1"],
        objective="repair-aware SFT export",
        dataset_kind="sft",
        provenance_refs=["trace.source.1"],
        metadata={"frozen": True},
    )
    score = TrainingExampleScore(
        id="training.score.1",
        example_id="training.example.1",
        score=0.75,
        dataset_kind="sft",
        training_signal=0.6,
        correction_support=0.7,
        trust_support=0.8,
        stability_support=0.9,
        repair_support=0.4,
        projection_support=0.3,
        provenance_support=0.2,
        metadata={"rank": 1},
    )

    assert ModelObservation.from_json_dict(observation.to_json_dict()) == observation
    assert ModelCorrection.from_json_dict(correction.to_json_dict()) == correction
    assert TrainingSignal.from_json_dict(signal.to_json_dict()) == signal
    assert TrainingExample.from_json_dict(example.to_json_dict()) == example
    assert TrainingTrace.from_json_dict(trace.to_json_dict()) == trace
    assert TrainingExampleScore.from_json_dict(score.to_json_dict()) == score


def test_score_training_examples_filters_by_trace_and_exports_row() -> None:
    fabric = _fabric()
    examples = [_example("example.keep", correction_id="correction.good"), _example("example.skip", correction_id=None)]
    trace = TrainingTrace(
        id="trace.sft",
        fabric_id="fabric.training",
        model_ref="model.local",
        example_ids=["example.keep"],
        objective="continuity repair export",
        dataset_kind="sft",
        provenance_refs=[],
        metadata={},
    )
    correction = _correction("correction.good", improvement_score=0.9, confidence=0.8)

    report = score_training_examples(fabric, examples, trace=trace, corrections=[correction])

    assert report["fabric_id"] == "fabric.training"
    assert report["trace_id"] == "trace.sft"
    assert [item["example_id"] for item in report["ranked_training_examples"]] == ["example.keep"]
    row = report["ranked_training_examples"][0]["metadata"]["export_row"]
    assert row["input"] == "Prompt for example.keep"
    assert row["output"] == "Output for example.keep"
    assert row["correction"] == "Corrected output for correction.good"


def test_training_scoring_ranks_deterministically() -> None:
    fabric = _fabric()
    examples = [_example("example.b", correction_id=None), _example("example.a", correction_id=None)]
    signals = [
        TrainingSignal(id="signal.b", example_id="example.b", signal_type="preference", magnitude=0.4, confidence=0.5, source_refs=[], metadata={}),
        TrainingSignal(id="signal.a", example_id="example.a", signal_type="preference", magnitude=0.4, confidence=0.5, source_refs=[], metadata={}),
    ]

    report = score_training_examples(fabric, examples, signals=signals)

    assert [item["example_id"] for item in report["ranked_training_examples"]] == ["example.a", "example.b"]


def test_support_evidence_can_make_lower_raw_signal_rank_first() -> None:
    fabric = _fabric()
    high_raw_signal = _example("example.raw", correction_id=None)
    supported = _example(
        "example.supported",
        correction_id="correction.strong",
        trust_refs=["trust.supported"],
        stability_refs=["stability.supported"],
        repair_refs=["repair.supported"],
        projection_refs=["future.supported"],
        provenance_refs=["source.1", "source.2", "source.3"],
    )
    signals = [
        TrainingSignal(id="signal.raw", example_id="example.raw", signal_type="preference", magnitude=0.9, confidence=0.9, source_refs=[], metadata={}),
        TrainingSignal(id="signal.supported", example_id="example.supported", signal_type="preference", magnitude=0.4, confidence=0.5, source_refs=[], metadata={}),
    ]

    report = score_training_examples(
        fabric,
        [high_raw_signal, supported],
        corrections=[_correction("correction.strong", improvement_score=1.0, confidence=0.9)],
        signals=signals,
        trust_scores=[TrustScore(id="trust.supported", target_ref="example.supported", score=0.9, confidence=0.8, evidence_ids=[], vector_id=None, metadata={})],
        stability_scores=[
            ManifoldStabilityScore(
                id="stability.supported",
                region_ref="example.supported",
                score=0.85,
                stable=True,
                warning=False,
                threshold_id=None,
                confidence=0.8,
                metadata={},
            )
        ],
        repair_candidates=[
            RepairOperator(
                id="repair.supported",
                contradiction_ids=["contradiction.1"],
                operator_type="repair_context",
                affected_patch_ids=["patch.training"],
                expected_obstruction_delta=0.9,
                continuity_role_impact=0.5,
                repair_cost=0.1,
                confidence=0.8,
                metadata={},
            )
        ],
        projection_candidates=[_future_candidate("future.supported")],
    )

    ranked = report["ranked_training_examples"]
    assert ranked[0]["example_id"] == "example.supported"
    assert ranked[0]["training_signal"] < ranked[1]["training_signal"]
    assert ranked[0]["correction_support"] > ranked[1]["correction_support"]
    assert ranked[0]["trust_support"] > ranked[1]["trust_support"]
    assert ranked[0]["repair_support"] > ranked[1]["repair_support"]


def test_score_training_examples_does_not_mutate_fabric() -> None:
    fabric = _fabric()
    before = fabric.to_json_dict()

    report = score_training_examples(fabric, [_example("example.safe", correction_id=None)])

    assert report["fabric_id"] == "fabric.training"
    assert fabric.to_json_dict() == before


def _example(
    example_id: str,
    *,
    correction_id: str | None,
    trust_refs: list[str] | None = None,
    stability_refs: list[str] | None = None,
    repair_refs: list[str] | None = None,
    projection_refs: list[str] | None = None,
    provenance_refs: list[str] | None = None,
) -> TrainingExample:
    return TrainingExample(
        id=example_id,
        input_text=f"Prompt for {example_id}",
        output_text=f"Output for {example_id}",
        correction_id=correction_id,
        observation_ids=[],
        trust_refs=trust_refs or [],
        stability_refs=stability_refs or [],
        repair_refs=repair_refs or [],
        projection_refs=projection_refs or [],
        provenance_refs=provenance_refs or [],
        metadata={"dataset_kind": "preference"},
    )


def _correction(correction_id: str, *, improvement_score: float, confidence: float) -> ModelCorrection:
    return ModelCorrection(
        id=correction_id,
        observation_ids=[],
        correction_type="continuity_repair",
        target_ref="response.1",
        corrected_output=f"Corrected output for {correction_id}",
        improvement_score=improvement_score,
        confidence=confidence,
        source_refs=["source.correction"],
        metadata={},
    )


def _future_candidate(candidate_id: str) -> FutureStateCandidate:
    return FutureStateCandidate(
        id=candidate_id,
        projection=ProjectionObject(
            id="projection.supported",
            projection_type="likely_case",
            source_fabric_id="fabric.training",
            projected_fabric_id="fabric.training.future",
            repair_ids=["repair.supported"],
            horizon="next",
            expected_global_coherence=0.9,
            expected_obstruction_score=0.1,
            repair_history_refs=[],
            metadata={},
        ),
        supporting_repair_ids=["repair.supported"],
        coherence_delta=0.2,
        obstruction_delta=0.5,
        repair_support=0.9,
        confidence=0.8,
        projection_cost=0.1,
        metadata={},
    )


def _fabric() -> QSOFabric:
    fabric = QSOFabric(id="fabric.training")
    fabric.add_patch(
        Patch(
            id="patch.training",
            domain="system",
            basis=["|0>", "|1>"],
            state=QuantumStateObject(id="state.training", vector=[1 + 0j, 0j]),
        )
    )
    return fabric
