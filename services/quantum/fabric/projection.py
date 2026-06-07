"""Deterministic future-state projection primitives for QSO fabrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.fabric import QSOFabric
from services.quantum.fabric.repair import RepairOperator


@dataclass(frozen=True, slots=True)
class ProjectionObject:
    id: str
    projection_type: str
    source_fabric_id: str
    projected_fabric_id: str
    repair_ids: list[str]
    horizon: str
    expected_global_coherence: float
    expected_obstruction_score: float
    repair_history_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "projection_type": self.projection_type,
            "source_fabric_id": self.source_fabric_id,
            "projected_fabric_id": self.projected_fabric_id,
            "repair_ids": list(self.repair_ids),
            "horizon": self.horizon,
            "expected_global_coherence": self.expected_global_coherence,
            "expected_obstruction_score": self.expected_obstruction_score,
            "repair_history_refs": list(self.repair_history_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "ProjectionObject":
        return cls(
            id=str(data["id"]),
            projection_type=str(data["projection_type"]),
            source_fabric_id=str(data["source_fabric_id"]),
            projected_fabric_id=str(data["projected_fabric_id"]),
            repair_ids=[str(item) for item in data.get("repair_ids", [])],
            horizon=str(data.get("horizon", "")),
            expected_global_coherence=float(data.get("expected_global_coherence", 0.0)),
            expected_obstruction_score=float(data.get("expected_obstruction_score", 0.0)),
            repair_history_refs=[str(item) for item in data.get("repair_history_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class FutureStateCandidate:
    id: str
    projection: ProjectionObject
    supporting_repair_ids: list[str]
    coherence_delta: float
    obstruction_delta: float
    repair_support: float
    confidence: float
    projection_cost: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "projection": self.projection.to_json_dict(),
            "supporting_repair_ids": list(self.supporting_repair_ids),
            "coherence_delta": self.coherence_delta,
            "obstruction_delta": self.obstruction_delta,
            "repair_support": self.repair_support,
            "confidence": self.confidence,
            "projection_cost": self.projection_cost,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "FutureStateCandidate":
        return cls(
            id=str(data["id"]),
            projection=ProjectionObject.from_json_dict(dict(data["projection"])),
            supporting_repair_ids=[str(item) for item in data.get("supporting_repair_ids", [])],
            coherence_delta=float(data.get("coherence_delta", 0.0)),
            obstruction_delta=float(data.get("obstruction_delta", 0.0)),
            repair_support=float(data.get("repair_support", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            projection_cost=float(data.get("projection_cost", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class FutureStateScoringWeights:
    expected_global_coherence: float = 0.35
    obstruction_reduction: float = 0.30
    repair_support: float = 0.20
    confidence: float = 0.15
    projection_cost: float = 0.20


def score_future_state_candidates(
    fabric: QSOFabric,
    candidates: list[FutureStateCandidate],
    *,
    repairs: list[RepairOperator] | None = None,
    weights: FutureStateScoringWeights | None = None,
) -> dict[str, Any]:
    """Rank future-state projections without applying them to the fabric."""

    scoring_weights = weights or FutureStateScoringWeights()
    repair_index = {repair.id: repair for repair in repairs or []}
    ranked_candidates = []
    for candidate in sorted(candidates, key=lambda item: item.id):
        repair_history_support = _repair_history_support(candidate, repair_index)
        repair_support = max(0.0, candidate.repair_support) + repair_history_support
        obstruction_reduction = max(0.0, candidate.obstruction_delta)
        score = (
            scoring_weights.expected_global_coherence * max(0.0, candidate.projection.expected_global_coherence)
            + scoring_weights.obstruction_reduction * obstruction_reduction
            + scoring_weights.repair_support * repair_support
            + scoring_weights.confidence * candidate.confidence
            - scoring_weights.projection_cost * max(0.0, candidate.projection_cost)
        )
        ranked_candidates.append(
            {
                "candidate_id": candidate.id,
                "projection_id": candidate.projection.id,
                "score": score,
                "projection_type": candidate.projection.projection_type,
                "projected_fabric_id": candidate.projection.projected_fabric_id,
                "horizon": candidate.projection.horizon,
                "expected_global_coherence": candidate.projection.expected_global_coherence,
                "expected_obstruction_score": candidate.projection.expected_obstruction_score,
                "coherence_delta": candidate.coherence_delta,
                "obstruction_delta": candidate.obstruction_delta,
                "repair_support": repair_support,
                "confidence": candidate.confidence,
                "projection_cost": candidate.projection_cost,
                "supporting_repair_ids": list(candidate.supporting_repair_ids),
                "repair_history_refs": list(candidate.projection.repair_history_refs),
            }
        )

    ranked_candidates.sort(key=lambda item: (-float(item["score"]), str(item["candidate_id"])))
    return {
        "fabric_id": fabric.id,
        "ranked_future_states": ranked_candidates,
    }


def _repair_history_support(candidate: FutureStateCandidate, repair_index: dict[str, RepairOperator]) -> float:
    if not repair_index:
        return 0.0
    support = 0.0
    seen = set()
    for repair_id in [*candidate.supporting_repair_ids, *candidate.projection.repair_ids]:
        if repair_id in seen:
            continue
        seen.add(repair_id)
        repair = repair_index.get(repair_id)
        if repair is None:
            continue
        support += max(0.0, repair.expected_obstruction_delta) * max(0.0, repair.confidence)
    return support
