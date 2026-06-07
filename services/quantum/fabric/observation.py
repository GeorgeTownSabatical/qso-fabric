"""Deterministic observation primitives for QSO fabrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.fabric import QSOFabric
from services.quantum.fabric.trust import TrustScore


@dataclass(frozen=True, slots=True)
class ObservationObject:
    id: str
    observer_ref: str
    target_ref: str
    observation_type: str
    signal: str
    magnitude: float
    confidence: float
    source_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "observer_ref": self.observer_ref,
            "target_ref": self.target_ref,
            "observation_type": self.observation_type,
            "signal": self.signal,
            "magnitude": self.magnitude,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "ObservationObject":
        return cls(
            id=str(data["id"]),
            observer_ref=str(data["observer_ref"]),
            target_ref=str(data["target_ref"]),
            observation_type=str(data["observation_type"]),
            signal=str(data["signal"]),
            magnitude=float(data.get("magnitude", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ObservationFrame:
    id: str
    fabric_id: str
    observation_ids: list[str]
    horizon: str
    context_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "fabric_id": self.fabric_id,
            "observation_ids": list(self.observation_ids),
            "horizon": self.horizon,
            "context_refs": list(self.context_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "ObservationFrame":
        return cls(
            id=str(data["id"]),
            fabric_id=str(data["fabric_id"]),
            observation_ids=[str(item) for item in data.get("observation_ids", [])],
            horizon=str(data.get("horizon", "")),
            context_refs=[str(item) for item in data.get("context_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ObservationScore:
    id: str
    observation_id: str
    target_ref: str
    score: float
    relevance: float
    confidence: float
    trust_support: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "observation_id": self.observation_id,
            "target_ref": self.target_ref,
            "score": self.score,
            "relevance": self.relevance,
            "confidence": self.confidence,
            "trust_support": self.trust_support,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "ObservationScore":
        return cls(
            id=str(data["id"]),
            observation_id=str(data["observation_id"]),
            target_ref=str(data["target_ref"]),
            score=float(data.get("score", 0.0)),
            relevance=float(data.get("relevance", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            trust_support=float(data.get("trust_support", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ObservationScoringWeights:
    magnitude: float = 0.35
    confidence: float = 0.25
    trust_support: float = 0.25
    source_support: float = 0.15


def score_observations(
    fabric: QSOFabric,
    observations: list[ObservationObject],
    *,
    frame: ObservationFrame | None = None,
    trust_scores: list[TrustScore] | None = None,
    weights: ObservationScoringWeights | None = None,
) -> dict[str, Any]:
    """Rank observations without modifying fabric state."""

    scoring_weights = weights or ObservationScoringWeights()
    trust_index = {trust_score.target_ref: trust_score for trust_score in trust_scores or []}
    frame_ids = set(frame.observation_ids) if frame is not None and frame.observation_ids else None
    ranked_observations = []
    for observation in sorted(observations, key=lambda item: item.id):
        if frame_ids is not None and observation.id not in frame_ids:
            continue
        trust_support = _trust_support(observation, trust_index)
        source_support = len(set(observation.source_refs)) / max(1, len(observation.source_refs) or 1)
        relevance = max(0.0, observation.magnitude) * max(0.0, observation.confidence)
        score = (
            scoring_weights.magnitude * max(0.0, observation.magnitude)
            + scoring_weights.confidence * max(0.0, observation.confidence)
            + scoring_weights.trust_support * trust_support
            + scoring_weights.source_support * source_support
        )
        ranked_observations.append(
            ObservationScore(
                id=f"observation.score.{observation.id}",
                observation_id=observation.id,
                target_ref=observation.target_ref,
                score=score,
                relevance=relevance,
                confidence=observation.confidence,
                trust_support=trust_support,
                metadata={
                    "observation_type": observation.observation_type,
                    "signal": observation.signal,
                    "source_support": source_support,
                },
            ).to_json_dict()
        )

    ranked_observations.sort(key=lambda item: (-float(item["score"]), str(item["observation_id"])))
    return {
        "fabric_id": fabric.id,
        "frame_id": frame.id if frame is not None else None,
        "ranked_observations": ranked_observations,
    }


def _trust_support(observation: ObservationObject, trust_index: dict[str, TrustScore]) -> float:
    trust_score = trust_index.get(observation.target_ref)
    if trust_score is None:
        return 0.0
    return max(0.0, trust_score.score) * max(0.0, trust_score.confidence)
