"""Deterministic model-training trace primitives for QSO fabrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.fabric import QSOFabric
from services.quantum.fabric.projection import FutureStateCandidate
from services.quantum.fabric.repair import RepairOperator
from services.quantum.fabric.stability import ManifoldStabilityScore
from services.quantum.fabric.trust import TrustScore


@dataclass(frozen=True, slots=True)
class ModelObservation:
    id: str
    model_ref: str
    input_ref: str
    output_ref: str
    observation_type: str
    magnitude: float
    confidence: float
    source_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_ref": self.model_ref,
            "input_ref": self.input_ref,
            "output_ref": self.output_ref,
            "observation_type": self.observation_type,
            "magnitude": self.magnitude,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "ModelObservation":
        return cls(
            id=str(data["id"]),
            model_ref=str(data["model_ref"]),
            input_ref=str(data["input_ref"]),
            output_ref=str(data["output_ref"]),
            observation_type=str(data["observation_type"]),
            magnitude=float(data.get("magnitude", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ModelCorrection:
    id: str
    observation_ids: list[str]
    correction_type: str
    target_ref: str
    corrected_output: str
    improvement_score: float
    confidence: float
    source_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "observation_ids": list(self.observation_ids),
            "correction_type": self.correction_type,
            "target_ref": self.target_ref,
            "corrected_output": self.corrected_output,
            "improvement_score": self.improvement_score,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "ModelCorrection":
        return cls(
            id=str(data["id"]),
            observation_ids=[str(item) for item in data.get("observation_ids", [])],
            correction_type=str(data["correction_type"]),
            target_ref=str(data["target_ref"]),
            corrected_output=str(data.get("corrected_output", "")),
            improvement_score=float(data.get("improvement_score", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class TrainingSignal:
    id: str
    example_id: str
    signal_type: str
    magnitude: float
    confidence: float
    source_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "example_id": self.example_id,
            "signal_type": self.signal_type,
            "magnitude": self.magnitude,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "TrainingSignal":
        return cls(
            id=str(data["id"]),
            example_id=str(data["example_id"]),
            signal_type=str(data["signal_type"]),
            magnitude=float(data.get("magnitude", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class TrainingExample:
    id: str
    input_text: str
    output_text: str
    correction_id: str | None
    observation_ids: list[str]
    trust_refs: list[str]
    stability_refs: list[str]
    repair_refs: list[str]
    projection_refs: list[str]
    provenance_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "input_text": self.input_text,
            "output_text": self.output_text,
            "correction_id": self.correction_id,
            "observation_ids": list(self.observation_ids),
            "trust_refs": list(self.trust_refs),
            "stability_refs": list(self.stability_refs),
            "repair_refs": list(self.repair_refs),
            "projection_refs": list(self.projection_refs),
            "provenance_refs": list(self.provenance_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "TrainingExample":
        raw_correction_id = data.get("correction_id")
        return cls(
            id=str(data["id"]),
            input_text=str(data.get("input_text", "")),
            output_text=str(data.get("output_text", "")),
            correction_id=str(raw_correction_id) if raw_correction_id is not None else None,
            observation_ids=[str(item) for item in data.get("observation_ids", [])],
            trust_refs=[str(item) for item in data.get("trust_refs", [])],
            stability_refs=[str(item) for item in data.get("stability_refs", [])],
            repair_refs=[str(item) for item in data.get("repair_refs", [])],
            projection_refs=[str(item) for item in data.get("projection_refs", [])],
            provenance_refs=[str(item) for item in data.get("provenance_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class TrainingTrace:
    id: str
    fabric_id: str
    model_ref: str
    example_ids: list[str]
    objective: str
    dataset_kind: str
    provenance_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "fabric_id": self.fabric_id,
            "model_ref": self.model_ref,
            "example_ids": list(self.example_ids),
            "objective": self.objective,
            "dataset_kind": self.dataset_kind,
            "provenance_refs": list(self.provenance_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "TrainingTrace":
        return cls(
            id=str(data["id"]),
            fabric_id=str(data["fabric_id"]),
            model_ref=str(data["model_ref"]),
            example_ids=[str(item) for item in data.get("example_ids", [])],
            objective=str(data.get("objective", "")),
            dataset_kind=str(data.get("dataset_kind", "")),
            provenance_refs=[str(item) for item in data.get("provenance_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class TrainingExampleScore:
    id: str
    example_id: str
    score: float
    dataset_kind: str
    training_signal: float
    correction_support: float
    trust_support: float
    stability_support: float
    repair_support: float
    projection_support: float
    provenance_support: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "example_id": self.example_id,
            "score": self.score,
            "dataset_kind": self.dataset_kind,
            "training_signal": self.training_signal,
            "correction_support": self.correction_support,
            "trust_support": self.trust_support,
            "stability_support": self.stability_support,
            "repair_support": self.repair_support,
            "projection_support": self.projection_support,
            "provenance_support": self.provenance_support,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "TrainingExampleScore":
        return cls(
            id=str(data["id"]),
            example_id=str(data["example_id"]),
            score=float(data.get("score", 0.0)),
            dataset_kind=str(data.get("dataset_kind", "")),
            training_signal=float(data.get("training_signal", 0.0)),
            correction_support=float(data.get("correction_support", 0.0)),
            trust_support=float(data.get("trust_support", 0.0)),
            stability_support=float(data.get("stability_support", 0.0)),
            repair_support=float(data.get("repair_support", 0.0)),
            projection_support=float(data.get("projection_support", 0.0)),
            provenance_support=float(data.get("provenance_support", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class TrainingScoringWeights:
    training_signal: float = 0.25
    correction_support: float = 0.20
    trust_support: float = 0.15
    stability_support: float = 0.15
    repair_support: float = 0.10
    projection_support: float = 0.10
    provenance_support: float = 0.05


def score_training_examples(
    fabric: QSOFabric,
    examples: list[TrainingExample],
    *,
    trace: TrainingTrace | None = None,
    observations: list[ModelObservation] | None = None,
    corrections: list[ModelCorrection] | None = None,
    signals: list[TrainingSignal] | None = None,
    trust_scores: list[TrustScore] | None = None,
    stability_scores: list[ManifoldStabilityScore] | None = None,
    repair_candidates: list[RepairOperator] | None = None,
    projection_candidates: list[FutureStateCandidate] | None = None,
    weights: TrainingScoringWeights | None = None,
) -> dict[str, Any]:
    """Rank model-training examples without training models or mutating fabric."""

    scoring_weights = weights or TrainingScoringWeights()
    trace_ids = set(trace.example_ids) if trace is not None and trace.example_ids else None
    observation_index = {observation.id: observation for observation in observations or []}
    correction_index = {correction.id: correction for correction in corrections or []}
    signals_by_example = _signals_by_example(signals or [])
    trust_index = {trust_score.id: trust_score for trust_score in trust_scores or []}
    stability_index = {stability_score.id: stability_score for stability_score in stability_scores or []}
    repair_index = {repair.id: repair for repair in repair_candidates or []}
    projection_index = {candidate.id: candidate for candidate in projection_candidates or []}

    ranked_examples = []
    for example in sorted(examples, key=lambda item: item.id):
        if trace_ids is not None and example.id not in trace_ids:
            continue
        training_signal = _training_signal(example.id, signals_by_example)
        correction_support = _correction_support(example, correction_index)
        trust_support = _trust_support(example, trust_index)
        stability_support = _stability_support(example, stability_index)
        repair_support = _repair_support(example, repair_index)
        projection_support = _projection_support(example, projection_index)
        provenance_support = _provenance_support(example)
        score = (
            scoring_weights.training_signal * training_signal
            + scoring_weights.correction_support * correction_support
            + scoring_weights.trust_support * trust_support
            + scoring_weights.stability_support * stability_support
            + scoring_weights.repair_support * repair_support
            + scoring_weights.projection_support * projection_support
            + scoring_weights.provenance_support * provenance_support
        )
        ranked_examples.append(
            TrainingExampleScore(
                id=f"training.score.{example.id}",
                example_id=example.id,
                score=score,
                dataset_kind=trace.dataset_kind if trace is not None else str(example.metadata.get("dataset_kind", "")),
                training_signal=training_signal,
                correction_support=correction_support,
                trust_support=trust_support,
                stability_support=stability_support,
                repair_support=repair_support,
                projection_support=projection_support,
                provenance_support=provenance_support,
                metadata={
                    "observation_support": _observation_support(example, observation_index),
                    "export_row": _export_row(example, correction_index),
                },
            ).to_json_dict()
        )

    ranked_examples.sort(key=lambda item: (-float(item["score"]), str(item["example_id"])))
    return {
        "fabric_id": fabric.id,
        "trace_id": trace.id if trace is not None else None,
        "ranked_training_examples": ranked_examples,
    }


def _signals_by_example(signals: list[TrainingSignal]) -> dict[str, list[TrainingSignal]]:
    out: dict[str, list[TrainingSignal]] = {}
    for signal in signals:
        out.setdefault(signal.example_id, []).append(signal)
    return out


def _training_signal(example_id: str, signals_by_example: dict[str, list[TrainingSignal]]) -> float:
    matching = signals_by_example.get(example_id, [])
    if not matching:
        return 0.0
    return sum(max(0.0, item.magnitude) * max(0.0, item.confidence) for item in matching) / len(matching)


def _correction_support(example: TrainingExample, correction_index: dict[str, ModelCorrection]) -> float:
    if example.correction_id is None:
        return 0.0
    correction = correction_index.get(example.correction_id)
    if correction is None:
        return 0.0
    return max(0.0, correction.improvement_score) * max(0.0, correction.confidence)


def _trust_support(example: TrainingExample, trust_index: dict[str, TrustScore]) -> float:
    matching = [trust_index[item] for item in example.trust_refs if item in trust_index]
    if not matching:
        return 0.0
    return sum(max(0.0, item.score) * max(0.0, item.confidence) for item in matching) / len(matching)


def _stability_support(example: TrainingExample, stability_index: dict[str, ManifoldStabilityScore]) -> float:
    matching = [stability_index[item] for item in example.stability_refs if item in stability_index]
    if not matching:
        return 0.0
    return sum(max(0.0, item.score) * max(0.0, item.confidence) for item in matching) / len(matching)


def _repair_support(example: TrainingExample, repair_index: dict[str, RepairOperator]) -> float:
    matching = [repair_index[item] for item in example.repair_refs if item in repair_index]
    if not matching:
        return 0.0
    return sum(max(0.0, item.expected_obstruction_delta) * max(0.0, item.confidence) for item in matching) / len(matching)


def _projection_support(example: TrainingExample, projection_index: dict[str, FutureStateCandidate]) -> float:
    matching = [projection_index[item] for item in example.projection_refs if item in projection_index]
    if not matching:
        return 0.0
    return sum(max(0.0, item.repair_support) * max(0.0, item.confidence) for item in matching) / len(matching)


def _provenance_support(example: TrainingExample) -> float:
    return min(1.0, len(set(example.provenance_refs)) / 3.0)


def _observation_support(example: TrainingExample, observation_index: dict[str, ModelObservation]) -> float:
    matching = [observation_index[item] for item in example.observation_ids if item in observation_index]
    if not matching:
        return 0.0
    return sum(max(0.0, item.magnitude) * max(0.0, item.confidence) for item in matching) / len(matching)


def _export_row(example: TrainingExample, correction_index: dict[str, ModelCorrection]) -> dict[str, Any]:
    correction = correction_index.get(example.correction_id or "")
    return {
        "input": example.input_text,
        "output": example.output_text,
        "correction": correction.corrected_output if correction is not None else None,
        "trust_refs": list(example.trust_refs),
        "stability_refs": list(example.stability_refs),
        "repair_refs": list(example.repair_refs),
        "projection_refs": list(example.projection_refs),
        "provenance_refs": list(example.provenance_refs),
    }
