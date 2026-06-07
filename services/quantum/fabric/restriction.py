"""Restriction maps between local patch state spaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.state import QuantumStateObject


def _coerce_matrix(rows: list[list[complex]] | tuple[tuple[complex, ...], ...]) -> tuple[tuple[complex, ...], ...]:
    matrix = tuple(tuple(complex(value) for value in row) for row in rows)
    if not matrix:
        raise ValueError("projection matrix cannot be empty")
    width = len(matrix[0])
    if width == 0:
        raise ValueError("projection matrix cannot have empty rows")
    if any(len(row) != width for row in matrix):
        raise ValueError("projection matrix rows must have equal width")
    return matrix


@dataclass(slots=True)
class RestrictionMap:
    """Linear projection from one patch-local description into another space."""

    id: str
    source_patch: str
    target_patch: str
    projection: tuple[tuple[complex, ...], ...] | list[list[complex]]
    validation_rule: str = "dimension_match"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.projection = _coerce_matrix(self.projection)

    @property
    def output_dimension(self) -> int:
        return len(self.projection)

    @property
    def input_dimension(self) -> int:
        return len(self.projection[0])

    def apply(self, state: QuantumStateObject, *, target_state_id: str | None = None) -> QuantumStateObject:
        if state.dimension != self.input_dimension:
            raise ValueError("restriction map input dimension mismatch")
        projected = []
        for row in self.projection:
            projected.append(sum(weight * value for weight, value in zip(row, state.vector)))
        return QuantumStateObject(
            id=target_state_id or f"{state.id}@{self.id}",
            vector=tuple(projected),
            phase=state.phase,
            uncertainty=state.uncertainty,
            metadata={"source_state_id": state.id, "restriction_map": self.id},
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_patch": self.source_patch,
            "target_patch": self.target_patch,
            "projection_real": [[value.real for value in row] for row in self.projection],
            "projection_imag": [[value.imag for value in row] for row in self.projection],
            "validation_rule": self.validation_rule,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "RestrictionMap":
        real = list(data["projection_real"])
        imag = list(data["projection_imag"])
        if len(real) != len(imag):
            raise ValueError("projection_real and projection_imag must have the same row count")
        projection = []
        for real_row, imag_row in zip(real, imag):
            if len(real_row) != len(imag_row):
                raise ValueError("projection_real and projection_imag row widths must match")
            projection.append([complex(r, i) for r, i in zip(real_row, imag_row)])
        return cls(
            id=str(data["id"]),
            source_patch=str(data["source_patch"]),
            target_patch=str(data["target_patch"]),
            projection=projection,
            validation_rule=str(data.get("validation_rule", "dimension_match")),
            metadata=dict(data.get("metadata", {})),
        )
