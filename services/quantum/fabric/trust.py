"""Deterministic trust mathematics primitives for QSO fabrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.fabric import QSOFabric


@dataclass(frozen=True, slots=True)
class TrustEvidence:
    id: str
    source_ref: str
    target_ref: str
    evidence_type: str
    trust_delta: float
    confidence: float
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_ref": self.source_ref,
            "target_ref": self.target_ref,
            "evidence_type": self.evidence_type,
            "trust_delta": self.trust_delta,
            "confidence": self.confidence,
            "weight": self.weight,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "TrustEvidence":
        return cls(
            id=str(data["id"]),
            source_ref=str(data["source_ref"]),
            target_ref=str(data["target_ref"]),
            evidence_type=str(data["evidence_type"]),
            trust_delta=float(data.get("trust_delta", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            weight=float(data.get("weight", 1.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class TrustVector:
    id: str
    target_ref: str
    dimensions: dict[str, float]
    evidence_ids: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_ref": self.target_ref,
            "dimensions": {str(key): float(value) for key, value in sorted(self.dimensions.items())},
            "evidence_ids": list(self.evidence_ids),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "TrustVector":
        return cls(
            id=str(data["id"]),
            target_ref=str(data["target_ref"]),
            dimensions={str(key): float(value) for key, value in dict(data.get("dimensions", {})).items()},
            evidence_ids=[str(item) for item in data.get("evidence_ids", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class TrustPropagationRule:
    id: str
    rule_type: str
    source_refs: list[str]
    target_ref: str
    propagation_weight: float
    decay: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "rule_type": self.rule_type,
            "source_refs": list(self.source_refs),
            "target_ref": self.target_ref,
            "propagation_weight": self.propagation_weight,
            "decay": self.decay,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "TrustPropagationRule":
        return cls(
            id=str(data["id"]),
            rule_type=str(data["rule_type"]),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            target_ref=str(data["target_ref"]),
            propagation_weight=float(data.get("propagation_weight", 0.0)),
            decay=float(data.get("decay", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class TrustScore:
    id: str
    target_ref: str
    score: float
    confidence: float
    evidence_ids: list[str]
    vector_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_ref": self.target_ref,
            "score": self.score,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "vector_id": self.vector_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "TrustScore":
        raw_vector_id = data.get("vector_id")
        return cls(
            id=str(data["id"]),
            target_ref=str(data["target_ref"]),
            score=float(data.get("score", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            evidence_ids=[str(item) for item in data.get("evidence_ids", [])],
            vector_id=str(raw_vector_id) if raw_vector_id is not None else None,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class TrustScoringWeights:
    vector_score: float = 0.45
    evidence_score: float = 0.35
    propagation_score: float = 0.20
    confidence: float = 0.15


def score_trust(
    fabric: QSOFabric,
    vectors: list[TrustVector],
    evidence: list[TrustEvidence],
    *,
    propagation_rules: list[TrustPropagationRule] | None = None,
    weights: TrustScoringWeights | None = None,
) -> dict[str, Any]:
    """Rank trust targets without mutating fabric or making routing decisions."""

    scoring_weights = weights or TrustScoringWeights()
    rules = propagation_rules or []
    evidence_by_target = _evidence_by_target(evidence)
    rules_by_target = _rules_by_target(rules)
    vector_by_target = {vector.target_ref: vector for vector in vectors}
    target_refs = sorted(set(vector_by_target) | set(evidence_by_target) | set(rules_by_target))
    ranked_trust = []
    for target_ref in target_refs:
        vector = vector_by_target.get(target_ref)
        target_evidence = evidence_by_target.get(target_ref, [])
        target_rules = rules_by_target.get(target_ref, [])
        vector_score = _vector_score(vector)
        evidence_score = _evidence_score(target_evidence)
        propagation_score = _propagation_score(target_rules, vector_by_target)
        confidence = _confidence(target_evidence, vector, target_rules)
        score = (
            scoring_weights.vector_score * vector_score
            + scoring_weights.evidence_score * evidence_score
            + scoring_weights.propagation_score * propagation_score
            + scoring_weights.confidence * confidence
        )
        ranked_trust.append(
            TrustScore(
                id=f"trust.score.{target_ref}",
                target_ref=target_ref,
                score=score,
                confidence=confidence,
                evidence_ids=[item.id for item in sorted(target_evidence, key=lambda item: item.id)],
                vector_id=vector.id if vector is not None else None,
                metadata={
                    "vector_score": vector_score,
                    "evidence_score": evidence_score,
                    "propagation_score": propagation_score,
                },
            ).to_json_dict()
        )

    ranked_trust.sort(key=lambda item: (-float(item["score"]), str(item["target_ref"])))
    return {
        "fabric_id": fabric.id,
        "ranked_trust": ranked_trust,
    }


def _evidence_by_target(evidence: list[TrustEvidence]) -> dict[str, list[TrustEvidence]]:
    out: dict[str, list[TrustEvidence]] = {}
    for item in evidence:
        out.setdefault(item.target_ref, []).append(item)
    return out


def _rules_by_target(rules: list[TrustPropagationRule]) -> dict[str, list[TrustPropagationRule]]:
    out: dict[str, list[TrustPropagationRule]] = {}
    for rule in rules:
        out.setdefault(rule.target_ref, []).append(rule)
    return out


def _vector_score(vector: TrustVector | None) -> float:
    if vector is None or not vector.dimensions:
        return 0.0
    return sum(float(value) for value in vector.dimensions.values()) / len(vector.dimensions)


def _evidence_score(evidence: list[TrustEvidence]) -> float:
    if not evidence:
        return 0.0
    total_weight = sum(max(0.0, item.weight) for item in evidence)
    if total_weight <= 0:
        return 0.0
    weighted = 0.0
    for item in evidence:
        weight = max(0.0, item.weight)
        weighted += item.trust_delta * item.confidence * weight
    return weighted / total_weight


def _propagation_score(rules: list[TrustPropagationRule], vector_by_target: dict[str, TrustVector]) -> float:
    if not rules:
        return 0.0
    total = 0.0
    for rule in rules:
        source_scores = [_vector_score(vector_by_target.get(source_ref)) for source_ref in rule.source_refs]
        source_score = sum(source_scores) / len(source_scores) if source_scores else 0.0
        total += source_score * max(0.0, rule.propagation_weight) * (1.0 - max(0.0, rule.decay))
    return total / len(rules)


def _confidence(evidence: list[TrustEvidence], vector: TrustVector | None, rules: list[TrustPropagationRule]) -> float:
    values = [max(0.0, item.confidence) for item in evidence]
    if vector is not None:
        values.append(1.0 if vector.dimensions else 0.0)
    values.extend(max(0.0, min(1.0, rule.propagation_weight)) for rule in rules)
    if not values:
        return 0.0
    return sum(values) / len(values)
