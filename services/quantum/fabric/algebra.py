"""Descriptive state algebra primitives for QSO fabrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.fabric import QSOFabric
from services.quantum.fabric.trust import TrustScore


@dataclass(frozen=True, slots=True)
class StateTransform:
    id: str
    transform_type: str
    source_state_ids: list[str]
    target_state_ids: list[str]
    expected_coherence_delta: float
    expected_obstruction_delta: float
    confidence: float
    cost: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "transform_type": self.transform_type,
            "source_state_ids": list(self.source_state_ids),
            "target_state_ids": list(self.target_state_ids),
            "expected_coherence_delta": self.expected_coherence_delta,
            "expected_obstruction_delta": self.expected_obstruction_delta,
            "confidence": self.confidence,
            "cost": self.cost,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "StateTransform":
        return cls(
            id=str(data["id"]),
            transform_type=str(data["transform_type"]),
            source_state_ids=[str(item) for item in data.get("source_state_ids", [])],
            target_state_ids=[str(item) for item in data.get("target_state_ids", [])],
            expected_coherence_delta=float(data.get("expected_coherence_delta", 0.0)),
            expected_obstruction_delta=float(data.get("expected_obstruction_delta", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            cost=float(data.get("cost", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class StateMerge:
    id: str
    left_state_id: str
    right_state_id: str
    merged_state_id: str
    transform_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "left_state_id": self.left_state_id,
            "right_state_id": self.right_state_id,
            "merged_state_id": self.merged_state_id,
            "transform_id": self.transform_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "StateMerge":
        return cls(
            id=str(data["id"]),
            left_state_id=str(data["left_state_id"]),
            right_state_id=str(data["right_state_id"]),
            merged_state_id=str(data["merged_state_id"]),
            transform_id=str(data["transform_id"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class StateSplit:
    id: str
    source_state_id: str
    split_state_ids: list[str]
    transform_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_state_id": self.source_state_id,
            "split_state_ids": list(self.split_state_ids),
            "transform_id": self.transform_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "StateSplit":
        return cls(
            id=str(data["id"]),
            source_state_id=str(data["source_state_id"]),
            split_state_ids=[str(item) for item in data.get("split_state_ids", [])],
            transform_id=str(data["transform_id"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class StateBranch:
    id: str
    source_state_id: str
    branch_state_id: str
    branch_type: str
    transform_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_state_id": self.source_state_id,
            "branch_state_id": self.branch_state_id,
            "branch_type": self.branch_type,
            "transform_id": self.transform_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "StateBranch":
        return cls(
            id=str(data["id"]),
            source_state_id=str(data["source_state_id"]),
            branch_state_id=str(data["branch_state_id"]),
            branch_type=str(data["branch_type"]),
            transform_id=str(data["transform_id"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class StateReconciliation:
    id: str
    transform_ids: list[str]
    source_state_ids: list[str]
    reconciled_state_id: str
    expected_coherence_delta: float
    expected_obstruction_delta: float
    trust_refs: list[str]
    confidence: float
    cost: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "transform_ids": list(self.transform_ids),
            "source_state_ids": list(self.source_state_ids),
            "reconciled_state_id": self.reconciled_state_id,
            "expected_coherence_delta": self.expected_coherence_delta,
            "expected_obstruction_delta": self.expected_obstruction_delta,
            "trust_refs": list(self.trust_refs),
            "confidence": self.confidence,
            "cost": self.cost,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "StateReconciliation":
        return cls(
            id=str(data["id"]),
            transform_ids=[str(item) for item in data.get("transform_ids", [])],
            source_state_ids=[str(item) for item in data.get("source_state_ids", [])],
            reconciled_state_id=str(data["reconciled_state_id"]),
            expected_coherence_delta=float(data.get("expected_coherence_delta", 0.0)),
            expected_obstruction_delta=float(data.get("expected_obstruction_delta", 0.0)),
            trust_refs=[str(item) for item in data.get("trust_refs", [])],
            confidence=float(data.get("confidence", 0.0)),
            cost=float(data.get("cost", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ReconciliationScoringWeights:
    coherence_delta: float = 0.30
    obstruction_delta: float = 0.30
    trust_support: float = 0.20
    confidence: float = 0.15
    cost: float = 0.20


def score_reconciliation(
    fabric: QSOFabric,
    reconciliations: list[StateReconciliation],
    *,
    transforms: list[StateTransform] | None = None,
    trust_scores: list[TrustScore] | None = None,
    weights: ReconciliationScoringWeights | None = None,
) -> dict[str, Any]:
    """Rank reconciliation descriptions without applying state changes."""

    scoring_weights = weights or ReconciliationScoringWeights()
    transform_index = {transform.id: transform for transform in transforms or []}
    trust_index = {trust_score.id: trust_score for trust_score in trust_scores or []}
    ranked_reconciliations = []
    for reconciliation in sorted(reconciliations, key=lambda item: item.id):
        transform_support = _transform_support(reconciliation, transform_index)
        trust_support = _trust_support(reconciliation, trust_index)
        coherence_delta = max(0.0, reconciliation.expected_coherence_delta) + transform_support["coherence_delta"]
        obstruction_delta = max(0.0, reconciliation.expected_obstruction_delta) + transform_support["obstruction_delta"]
        confidence = _combined_confidence(reconciliation, transform_support["confidence"], trust_support)
        score = (
            scoring_weights.coherence_delta * coherence_delta
            + scoring_weights.obstruction_delta * obstruction_delta
            + scoring_weights.trust_support * trust_support
            + scoring_weights.confidence * confidence
            - scoring_weights.cost * max(0.0, reconciliation.cost)
        )
        ranked_reconciliations.append(
            {
                "reconciliation_id": reconciliation.id,
                "score": score,
                "reconciled_state_id": reconciliation.reconciled_state_id,
                "transform_ids": list(reconciliation.transform_ids),
                "source_state_ids": list(reconciliation.source_state_ids),
                "expected_coherence_delta": reconciliation.expected_coherence_delta,
                "expected_obstruction_delta": reconciliation.expected_obstruction_delta,
                "trust_support": trust_support,
                "confidence": confidence,
                "cost": reconciliation.cost,
            }
        )

    ranked_reconciliations.sort(key=lambda item: (-float(item["score"]), str(item["reconciliation_id"])))
    return {
        "fabric_id": fabric.id,
        "ranked_reconciliations": ranked_reconciliations,
    }


def _transform_support(reconciliation: StateReconciliation, transform_index: dict[str, StateTransform]) -> dict[str, float]:
    coherence_delta = 0.0
    obstruction_delta = 0.0
    confidence_values = []
    seen = set()
    for transform_id in reconciliation.transform_ids:
        if transform_id in seen:
            continue
        seen.add(transform_id)
        transform = transform_index.get(transform_id)
        if transform is None:
            continue
        coherence_delta += max(0.0, transform.expected_coherence_delta)
        obstruction_delta += max(0.0, transform.expected_obstruction_delta)
        confidence_values.append(max(0.0, transform.confidence))
    return {
        "coherence_delta": coherence_delta,
        "obstruction_delta": obstruction_delta,
        "confidence": sum(confidence_values) / len(confidence_values) if confidence_values else 0.0,
    }


def _trust_support(reconciliation: StateReconciliation, trust_index: dict[str, TrustScore]) -> float:
    if not reconciliation.trust_refs:
        return 0.0
    total = 0.0
    seen = set()
    for trust_ref in reconciliation.trust_refs:
        if trust_ref in seen:
            continue
        seen.add(trust_ref)
        trust_score = trust_index.get(trust_ref)
        if trust_score is None:
            continue
        total += max(0.0, trust_score.score) * max(0.0, trust_score.confidence)
    return total


def _combined_confidence(reconciliation: StateReconciliation, transform_confidence: float, trust_support: float) -> float:
    values = [max(0.0, reconciliation.confidence)]
    if transform_confidence > 0:
        values.append(transform_confidence)
    if trust_support > 0:
        values.append(min(1.0, trust_support))
    return sum(values) / len(values)
