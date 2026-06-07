"""Deterministic correlation metrics for QSO fabrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.fabric import QSOFabric
from services.quantum.fabric.observation import ObservationObject
from services.quantum.fabric.trust import TrustScore


@dataclass(frozen=True, slots=True)
class CorrelationObject:
    id: str
    correlation_type: str
    left_ref: str
    right_ref: str
    strength: float
    confidence: float
    source_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "correlation_type": self.correlation_type,
            "left_ref": self.left_ref,
            "right_ref": self.right_ref,
            "strength": self.strength,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "CorrelationObject":
        return cls(
            id=str(data["id"]),
            correlation_type=str(data["correlation_type"]),
            left_ref=str(data["left_ref"]),
            right_ref=str(data["right_ref"]),
            strength=float(data.get("strength", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class CorrelationMetric:
    id: str
    correlation_id: str
    metric_type: str
    value: float
    confidence: float
    source_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "correlation_id": self.correlation_id,
            "metric_type": self.metric_type,
            "value": self.value,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "CorrelationMetric":
        return cls(
            id=str(data["id"]),
            correlation_id=str(data["correlation_id"]),
            metric_type=str(data["metric_type"]),
            value=float(data.get("value", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class CorrelationCluster:
    id: str
    correlation_ids: list[str]
    member_refs: list[str]
    centroid_ref: str | None = None
    cohesion_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "correlation_ids": list(self.correlation_ids),
            "member_refs": list(self.member_refs),
            "centroid_ref": self.centroid_ref,
            "cohesion_score": self.cohesion_score,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "CorrelationCluster":
        raw_centroid_ref = data.get("centroid_ref")
        return cls(
            id=str(data["id"]),
            correlation_ids=[str(item) for item in data.get("correlation_ids", [])],
            member_refs=[str(item) for item in data.get("member_refs", [])],
            centroid_ref=str(raw_centroid_ref) if raw_centroid_ref is not None else None,
            cohesion_score=float(data.get("cohesion_score", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class CorrelationScoringWeights:
    strength: float = 0.35
    confidence: float = 0.25
    trust_support: float = 0.20
    observation_support: float = 0.15
    source_support: float = 0.05


def score_correlations(
    fabric: QSOFabric,
    correlations: list[CorrelationObject],
    *,
    observations: list[ObservationObject] | None = None,
    trust_scores: list[TrustScore] | None = None,
    weights: CorrelationScoringWeights | None = None,
) -> dict[str, Any]:
    """Rank correlations without adding fabric edges or mutating state."""

    scoring_weights = weights or CorrelationScoringWeights()
    observation_index = _observations_by_target(observations or [])
    trust_index = {trust_score.target_ref: trust_score for trust_score in trust_scores or []}
    ranked_correlations = []
    for correlation in sorted(correlations, key=lambda item: item.id):
        trust_support = _trust_support(correlation, trust_index)
        observation_support = _observation_support(correlation, observation_index)
        source_support = _source_support(correlation.source_refs)
        score = (
            scoring_weights.strength * max(0.0, correlation.strength)
            + scoring_weights.confidence * max(0.0, correlation.confidence)
            + scoring_weights.trust_support * trust_support
            + scoring_weights.observation_support * observation_support
            + scoring_weights.source_support * source_support
        )
        ranked_correlations.append(
            {
                "correlation_id": correlation.id,
                "score": score,
                "correlation_type": correlation.correlation_type,
                "left_ref": correlation.left_ref,
                "right_ref": correlation.right_ref,
                "strength": correlation.strength,
                "confidence": correlation.confidence,
                "trust_support": trust_support,
                "observation_support": observation_support,
                "source_support": source_support,
                "source_refs": list(correlation.source_refs),
            }
        )

    ranked_correlations.sort(key=lambda item: (-float(item["score"]), str(item["correlation_id"])))
    return {
        "fabric_id": fabric.id,
        "ranked_correlations": ranked_correlations,
    }


def _observations_by_target(observations: list[ObservationObject]) -> dict[str, list[ObservationObject]]:
    out: dict[str, list[ObservationObject]] = {}
    for observation in observations:
        out.setdefault(observation.target_ref, []).append(observation)
    return out


def _trust_support(correlation: CorrelationObject, trust_index: dict[str, TrustScore]) -> float:
    total = 0.0
    seen = set()
    for target_ref in (correlation.left_ref, correlation.right_ref):
        if target_ref in seen:
            continue
        seen.add(target_ref)
        trust_score = trust_index.get(target_ref)
        if trust_score is None:
            continue
        total += max(0.0, trust_score.score) * max(0.0, trust_score.confidence)
    return total


def _observation_support(correlation: CorrelationObject, observation_index: dict[str, list[ObservationObject]]) -> float:
    observations = [
        *observation_index.get(correlation.left_ref, []),
        *observation_index.get(correlation.right_ref, []),
    ]
    if not observations:
        return 0.0
    total = 0.0
    for observation in observations:
        total += max(0.0, observation.magnitude) * max(0.0, observation.confidence)
    return total / len(observations)


def _source_support(source_refs: list[str]) -> float:
    if not source_refs:
        return 0.0
    return len(set(source_refs)) / len(source_refs)
