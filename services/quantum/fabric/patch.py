"""Patch-level local state assignments for the fabric kernel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.state import QuantumStateObject


@dataclass(slots=True)
class Patch:
    """A local region with a basis and attached quantum-inspired state."""

    id: str
    domain: str
    basis: tuple[str, ...] | list[str]
    state: QuantumStateObject
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.basis = tuple(str(item) for item in self.basis)
        if self.basis and len(self.basis) != self.state.dimension:
            raise ValueError("basis length must match state dimension")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "basis": list(self.basis),
            "state": self.state.to_json_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "Patch":
        return cls(
            id=str(data["id"]),
            domain=str(data["domain"]),
            basis=list(data.get("basis", [])),
            state=QuantumStateObject.from_json_dict(dict(data["state"])),
            metadata=dict(data.get("metadata", {})),
        )
