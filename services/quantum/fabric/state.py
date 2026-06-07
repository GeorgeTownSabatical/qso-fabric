"""Quantum-inspired local state containers for the fabric kernel."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Any

CONTINUITY_METADATA_KEYS = (
    "parent_state_id",
    "child_fabric_uri",
    "continuity_role",
    "retrieval_weight",
    "projection_horizon",
    "provenance_refs",
    "contradiction_refs",
    "repair_history_refs",
)


def _coerce_vector(values: list[complex] | tuple[complex, ...]) -> tuple[complex, ...]:
    vector = tuple(complex(value) for value in values)
    if not vector:
        raise ValueError("state vector cannot be empty")
    return vector


@dataclass(slots=True)
class QuantumStateObject:
    """Normalized local state vector with simple comparison metrics."""

    id: str
    vector: tuple[complex, ...] | list[complex]
    phase: float = 0.0
    uncertainty: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.vector = _coerce_vector(self.vector)
        self.normalize()

    @property
    def dimension(self) -> int:
        return len(self.vector)

    def norm(self) -> float:
        return sqrt(sum(abs(value) ** 2 for value in self.vector))

    def normalize(self) -> None:
        norm = self.norm()
        if norm == 0:
            raise ValueError("QuantumStateObject vector cannot be zero.")
        self.vector = tuple(value / norm for value in self.vector)

    def distance_to(self, other: "QuantumStateObject") -> float:
        if self.dimension != other.dimension:
            raise ValueError("Cannot compare states with different dimensions.")
        return sqrt(sum(abs(left - right) ** 2 for left, right in zip(self.vector, other.vector)))

    def fidelity_with(self, other: "QuantumStateObject") -> float:
        if self.dimension != other.dimension:
            raise ValueError("Cannot compare states with different dimensions.")
        inner = sum(left.conjugate() * right for left, right in zip(self.vector, other.vector))
        return float(abs(inner) ** 2)

    def continuity_metadata(self) -> dict[str, Any]:
        """Return future-self continuity metadata without changing wire shape."""

        return {key: self.metadata[key] for key in CONTINUITY_METADATA_KEYS if key in self.metadata}

    def continuity_value(self, key: str, default: Any = None) -> Any:
        if key not in CONTINUITY_METADATA_KEYS:
            raise KeyError(f"unknown continuity metadata key: {key}")
        return self.metadata.get(key, default)

    @property
    def parent_state_id(self) -> str | None:
        value = self.metadata.get("parent_state_id")
        return str(value) if value is not None else None

    @property
    def child_fabric_uri(self) -> str | None:
        value = self.metadata.get("child_fabric_uri")
        return str(value) if value is not None else None

    @property
    def continuity_role(self) -> str | None:
        value = self.metadata.get("continuity_role")
        return str(value) if value is not None else None

    @property
    def retrieval_weight(self) -> float:
        value = self.metadata.get("retrieval_weight", 1.0)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 1.0

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "vector_real": [value.real for value in self.vector],
            "vector_imag": [value.imag for value in self.vector],
            "phase": self.phase,
            "uncertainty": self.uncertainty,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "QuantumStateObject":
        real = list(data["vector_real"])
        imag = list(data["vector_imag"])
        if len(real) != len(imag):
            raise ValueError("vector_real and vector_imag must have the same length")
        vector = [complex(r, i) for r, i in zip(real, imag)]
        return cls(
            id=str(data["id"]),
            vector=vector,
            phase=float(data.get("phase", 0.0)),
            uncertainty=float(data.get("uncertainty", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )
