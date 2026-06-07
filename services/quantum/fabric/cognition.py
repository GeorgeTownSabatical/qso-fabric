"""Serializable cognitive state primitives for QSO fabrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CognitiveState:
    id: str
    state_ref: str
    cognitive_role: str
    activation: float
    confidence: float
    source_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "state_ref": self.state_ref,
            "cognitive_role": self.cognitive_role,
            "activation": self.activation,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "CognitiveState":
        return cls(
            id=str(data["id"]),
            state_ref=str(data["state_ref"]),
            cognitive_role=str(data["cognitive_role"]),
            activation=float(data.get("activation", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class AttentionField:
    id: str
    target_ref: str
    intensity: float
    focus: float
    radius: float
    source_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_ref": self.target_ref,
            "intensity": self.intensity,
            "focus": self.focus,
            "radius": self.radius,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "AttentionField":
        return cls(
            id=str(data["id"]),
            target_ref=str(data["target_ref"]),
            intensity=float(data.get("intensity", 0.0)),
            focus=float(data.get("focus", 0.0)),
            radius=float(data.get("radius", 1.0)),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class IntentSurface:
    id: str
    intent_ref: str
    priority: float
    confidence: float
    stability: float
    target_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "intent_ref": self.intent_ref,
            "priority": self.priority,
            "confidence": self.confidence,
            "stability": self.stability,
            "target_refs": list(self.target_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "IntentSurface":
        return cls(
            id=str(data["id"]),
            intent_ref=str(data["intent_ref"]),
            priority=float(data.get("priority", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            stability=float(data.get("stability", 0.0)),
            target_refs=[str(item) for item in data.get("target_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class MemoryTrace:
    id: str
    memory_ref: str
    patch_refs: list[str]
    strength: float
    recency: float
    source_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "memory_ref": self.memory_ref,
            "patch_refs": list(self.patch_refs),
            "strength": self.strength,
            "recency": self.recency,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "MemoryTrace":
        return cls(
            id=str(data["id"]),
            memory_ref=str(data["memory_ref"]),
            patch_refs=[str(item) for item in data.get("patch_refs", [])],
            strength=float(data.get("strength", 0.0)),
            recency=float(data.get("recency", 0.0)),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ReasoningPath:
    id: str
    path_refs: list[str]
    path_type: str
    confidence: float
    cost: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path_refs": list(self.path_refs),
            "path_type": self.path_type,
            "confidence": self.confidence,
            "cost": self.cost,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "ReasoningPath":
        return cls(
            id=str(data["id"]),
            path_refs=[str(item) for item in data.get("path_refs", [])],
            path_type=str(data["path_type"]),
            confidence=float(data.get("confidence", 0.0)),
            cost=float(data.get("cost", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class UncertaintyField:
    id: str
    target_ref: str
    uncertainty: float
    entropy: float
    source_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_ref": self.target_ref,
            "uncertainty": self.uncertainty,
            "entropy": self.entropy,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "UncertaintyField":
        return cls(
            id=str(data["id"]),
            target_ref=str(data["target_ref"]),
            uncertainty=float(data.get("uncertainty", 0.0)),
            entropy=float(data.get("entropy", 0.0)),
            source_refs=[str(item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )
