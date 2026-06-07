"""Repair-aware continuity primitives for QSO fabrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.fabric import QSOFabric


@dataclass(frozen=True, slots=True)
class ContradictionObject:
    id: str
    mismatch_type: str
    affected_patch_ids: list[str]
    affected_state_ids: list[str]
    source_refs: list[str]
    severity: float
    obstruction_score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mismatch_type": self.mismatch_type,
            "affected_patch_ids": list(self.affected_patch_ids),
            "affected_state_ids": list(self.affected_state_ids),
            "source_refs": list(self.source_refs),
            "severity": self.severity,
            "obstruction_score": self.obstruction_score,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "ContradictionObject":
        return cls(
            id=str(data["id"]),
            mismatch_type=str(data["mismatch_type"]),
            affected_patch_ids=[str(item) for item in data.get("affected_patch_ids", [])],
            affected_state_ids=[str(item) for item in data.get("affected_state_ids", [])],
            source_refs=[str(item) for item in data.get("source_refs", [])],
            severity=float(data.get("severity", 0.0)),
            obstruction_score=float(data.get("obstruction_score", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class RepairOperator:
    id: str
    contradiction_ids: list[str]
    operator_type: str
    affected_patch_ids: list[str]
    expected_obstruction_delta: float
    continuity_role_impact: float
    repair_cost: float
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "contradiction_ids": list(self.contradiction_ids),
            "operator_type": self.operator_type,
            "affected_patch_ids": list(self.affected_patch_ids),
            "expected_obstruction_delta": self.expected_obstruction_delta,
            "continuity_role_impact": self.continuity_role_impact,
            "repair_cost": self.repair_cost,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "RepairOperator":
        return cls(
            id=str(data["id"]),
            contradiction_ids=[str(item) for item in data.get("contradiction_ids", [])],
            operator_type=str(data["operator_type"]),
            affected_patch_ids=[str(item) for item in data.get("affected_patch_ids", [])],
            expected_obstruction_delta=float(data.get("expected_obstruction_delta", 0.0)),
            continuity_role_impact=float(data.get("continuity_role_impact", 0.0)),
            repair_cost=float(data.get("repair_cost", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class RepairScoringWeights:
    obstruction_reduction: float = 0.45
    continuity_role_impact: float = 0.20
    confidence: float = 0.15
    severity_coverage: float = 0.25
    repair_cost: float = 0.20


def score_repair_candidates(
    fabric: QSOFabric,
    contradictions: list[ContradictionObject],
    candidates: list[RepairOperator],
    *,
    weights: RepairScoringWeights | None = None,
) -> dict[str, Any]:
    """Rank repair proposals without applying them to the fabric."""

    scoring_weights = weights or RepairScoringWeights()
    contradiction_index = {contradiction.id: contradiction for contradiction in contradictions}
    total_severity = sum(max(0.0, contradiction.severity) for contradiction in contradictions)
    ranked_repairs = []
    for candidate in sorted(candidates, key=lambda item: item.id):
        severity_coverage = _severity_coverage(candidate, contradiction_index, total_severity)
        expected_obstruction_reduction = max(0.0, candidate.expected_obstruction_delta)
        score = (
            scoring_weights.obstruction_reduction * expected_obstruction_reduction
            + scoring_weights.continuity_role_impact * candidate.continuity_role_impact
            + scoring_weights.confidence * candidate.confidence
            + scoring_weights.severity_coverage * severity_coverage
            - scoring_weights.repair_cost * max(0.0, candidate.repair_cost)
        )
        ranked_repairs.append(
            {
                "repair_id": candidate.id,
                "score": score,
                "operator_type": candidate.operator_type,
                "contradiction_ids": list(candidate.contradiction_ids),
                "expected_obstruction_delta": candidate.expected_obstruction_delta,
                "continuity_role_impact": candidate.continuity_role_impact,
                "repair_cost": candidate.repair_cost,
                "confidence": candidate.confidence,
                "severity_coverage": severity_coverage,
            }
        )

    ranked_repairs.sort(key=lambda item: (-float(item["score"]), str(item["repair_id"])))
    return {
        "fabric_id": fabric.id,
        "ranked_repairs": ranked_repairs,
    }


def _severity_coverage(
    candidate: RepairOperator,
    contradiction_index: dict[str, ContradictionObject],
    total_severity: float,
) -> float:
    if total_severity <= 0:
        return 0.0
    covered = 0.0
    seen = set()
    for contradiction_id in candidate.contradiction_ids:
        if contradiction_id in seen:
            continue
        seen.add(contradiction_id)
        contradiction = contradiction_index.get(contradiction_id)
        if contradiction is None:
            continue
        covered += max(0.0, contradiction.severity)
    return covered / total_severity
