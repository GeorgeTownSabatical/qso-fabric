"""Deterministic manifold stability scoring for QSO fabrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.correlation import CorrelationObject
from services.quantum.fabric.fabric import QSOFabric
from services.quantum.fabric.observation import ObservationObject
from services.quantum.fabric.projection import FutureStateCandidate
from services.quantum.fabric.repair import RepairOperator
from services.quantum.fabric.trust import TrustScore


@dataclass(frozen=True, slots=True)
class StabilitySignal:
    id: str
    region_ref: str
    signal_type: str
    magnitude: float
    confidence: float
    source_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "region_ref": self.region_ref,
            "signal_type": self.signal_type,
            "magnitude": self.magnitude,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "StabilitySignal":
        return cls(
            id=str(data["id"]),
            region_ref=str(data["region_ref"]),
            signal_type=str(data["signal_type"]),
            magnitude=float(data.get("magnitude", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class StabilityThreshold:
    id: str
    region_ref: str
    minimum_score: float
    warning_score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "region_ref": self.region_ref,
            "minimum_score": self.minimum_score,
            "warning_score": self.warning_score,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "StabilityThreshold":
        return cls(
            id=str(data["id"]),
            region_ref=str(data["region_ref"]),
            minimum_score=float(data.get("minimum_score", 0.0)),
            warning_score=float(data.get("warning_score", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ManifoldStabilityScore:
    id: str
    region_ref: str
    score: float
    stable: bool
    warning: bool
    threshold_id: str | None
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "region_ref": self.region_ref,
            "score": self.score,
            "stable": self.stable,
            "warning": self.warning,
            "threshold_id": self.threshold_id,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "ManifoldStabilityScore":
        raw_threshold_id = data.get("threshold_id")
        return cls(
            id=str(data["id"]),
            region_ref=str(data["region_ref"]),
            score=float(data.get("score", 0.0)),
            stable=bool(data.get("stable", False)),
            warning=bool(data.get("warning", False)),
            threshold_id=str(raw_threshold_id) if raw_threshold_id is not None else None,
            confidence=float(data.get("confidence", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class StabilityScoringWeights:
    signal: float = 0.30
    correlation: float = 0.20
    observation: float = 0.15
    trust: float = 0.20
    repair: float = 0.10
    projection: float = 0.15
    instability_penalty: float = 0.25


def score_manifold_stability(
    fabric: QSOFabric,
    signals: list[StabilitySignal],
    thresholds: list[StabilityThreshold],
    *,
    correlations: list[CorrelationObject] | None = None,
    observations: list[ObservationObject] | None = None,
    trust_scores: list[TrustScore] | None = None,
    repair_candidates: list[RepairOperator] | None = None,
    projection_candidates: list[FutureStateCandidate] | None = None,
    weights: StabilityScoringWeights | None = None,
) -> dict[str, Any]:
    """Rank fabric regions by non-mutating manifold stability."""

    scoring_weights = weights or StabilityScoringWeights()
    threshold_index = {threshold.region_ref: threshold for threshold in thresholds}
    region_refs = sorted(
        set(threshold_index)
        | {signal.region_ref for signal in signals}
        | _region_refs_from_correlations(correlations or [])
        | {observation.target_ref for observation in observations or []}
        | {trust_score.target_ref for trust_score in trust_scores or []}
    )
    ranked_stability = []
    for region_ref in region_refs:
        signal_score, signal_confidence = _signal_score(region_ref, signals)
        correlation_support = _correlation_support(region_ref, correlations or [])
        observation_support = _observation_support(region_ref, observations or [])
        trust_support = _trust_support(region_ref, trust_scores or [])
        repair_support = _repair_support(region_ref, repair_candidates or [])
        projection_support = _projection_support(region_ref, projection_candidates or [])
        instability_penalty = _instability_penalty(region_ref, signals)
        score = (
            scoring_weights.signal * signal_score
            + scoring_weights.correlation * correlation_support
            + scoring_weights.observation * observation_support
            + scoring_weights.trust * trust_support
            + scoring_weights.repair * repair_support
            + scoring_weights.projection * projection_support
            - scoring_weights.instability_penalty * instability_penalty
        )
        threshold = threshold_index.get(region_ref)
        minimum_score = threshold.minimum_score if threshold is not None else 0.0
        warning_score = threshold.warning_score if threshold is not None else minimum_score
        stable = score >= minimum_score
        warning = score < warning_score
        ranked_stability.append(
            ManifoldStabilityScore(
                id=f"stability.score.{region_ref}",
                region_ref=region_ref,
                score=score,
                stable=stable,
                warning=warning,
                threshold_id=threshold.id if threshold is not None else None,
                confidence=signal_confidence,
                metadata={
                    "signal_score": signal_score,
                    "correlation_support": correlation_support,
                    "observation_support": observation_support,
                    "trust_support": trust_support,
                    "repair_support": repair_support,
                    "projection_support": projection_support,
                    "instability_penalty": instability_penalty,
                },
            ).to_json_dict()
        )

    ranked_stability.sort(key=lambda item: (-float(item["score"]), str(item["region_ref"])))
    return {
        "fabric_id": fabric.id,
        "ranked_stability": ranked_stability,
    }


def _region_refs_from_correlations(correlations: list[CorrelationObject]) -> set[str]:
    out = set()
    for correlation in correlations:
        out.add(correlation.left_ref)
        out.add(correlation.right_ref)
    return out


def _signal_score(region_ref: str, signals: list[StabilitySignal]) -> tuple[float, float]:
    matching = [signal for signal in signals if signal.region_ref == region_ref]
    if not matching:
        return 0.0, 0.0
    total = 0.0
    confidence = 0.0
    for signal in matching:
        total += max(0.0, signal.magnitude) * max(0.0, signal.confidence)
        confidence += max(0.0, signal.confidence)
    return total / len(matching), confidence / len(matching)


def _correlation_support(region_ref: str, correlations: list[CorrelationObject]) -> float:
    matching = [correlation for correlation in correlations if correlation.left_ref == region_ref or correlation.right_ref == region_ref]
    if not matching:
        return 0.0
    return sum(max(0.0, item.strength) * max(0.0, item.confidence) for item in matching) / len(matching)


def _observation_support(region_ref: str, observations: list[ObservationObject]) -> float:
    matching = [observation for observation in observations if observation.target_ref == region_ref]
    if not matching:
        return 0.0
    return sum(max(0.0, item.magnitude) * max(0.0, item.confidence) for item in matching) / len(matching)


def _trust_support(region_ref: str, trust_scores: list[TrustScore]) -> float:
    matching = [trust_score for trust_score in trust_scores if trust_score.target_ref == region_ref]
    if not matching:
        return 0.0
    return sum(max(0.0, item.score) * max(0.0, item.confidence) for item in matching) / len(matching)


def _repair_support(region_ref: str, repairs: list[RepairOperator]) -> float:
    matching = [repair for repair in repairs if region_ref in repair.affected_patch_ids]
    if not matching:
        return 0.0
    return sum(max(0.0, item.expected_obstruction_delta) * max(0.0, item.confidence) for item in matching) / len(matching)


def _projection_support(region_ref: str, projections: list[FutureStateCandidate]) -> float:
    matching = [candidate for candidate in projections if candidate.projection.projected_fabric_id == region_ref or candidate.projection.source_fabric_id == region_ref]
    if not matching:
        return 0.0
    return sum(max(0.0, item.projection.expected_global_coherence) * max(0.0, item.confidence) for item in matching) / len(matching)


def _instability_penalty(region_ref: str, signals: list[StabilitySignal]) -> float:
    penalties = [
        max(0.0, signal.magnitude) * max(0.0, signal.confidence)
        for signal in signals
        if signal.region_ref == region_ref and signal.signal_type.lower() in {"instability", "entropy", "backpressure"}
    ]
    if not penalties:
        return 0.0
    return sum(penalties) / len(penalties)
