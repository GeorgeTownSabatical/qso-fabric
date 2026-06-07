"""Overlap records connecting patch-local views through restriction maps."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from typing import Any

from services.quantum.fabric.patch import Patch
from services.quantum.fabric.restriction import RestrictionMap


@dataclass(slots=True)
class Overlap:
    """Compatibility contract for two local patch descriptions."""

    id: str
    patch_a: str
    patch_b: str
    shared_domain: tuple[str, ...] | list[str]
    restriction_a: RestrictionMap
    restriction_b: RestrictionMap
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.shared_domain = tuple(str(item) for item in self.shared_domain)
        if self.restriction_a.output_dimension != self.restriction_b.output_dimension:
            raise ValueError("overlap restrictions must project into the same dimension")

    def restricted_states(self, patch_a: Patch, patch_b: Patch) -> tuple[Any, Any]:
        if patch_a.id != self.patch_a or patch_b.id != self.patch_b:
            raise ValueError("overlap patch ids do not match supplied patches")
        return self.restriction_a.apply(patch_a.state), self.restriction_b.apply(patch_b.state)

    def mismatch(self, patch_a: Patch, patch_b: Patch) -> float:
        left, right = self.restricted_states(patch_a, patch_b)
        return left.distance_to(right)

    def fidelity(self, patch_a: Patch, patch_b: Patch) -> float:
        left, right = self.restricted_states(patch_a, patch_b)
        return left.fidelity_with(right)

    def coherence(self, patch_a: Patch, patch_b: Patch) -> float:
        return exp(-self.mismatch(patch_a, patch_b))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "patch_a": self.patch_a,
            "patch_b": self.patch_b,
            "shared_domain": list(self.shared_domain),
            "restriction_a": self.restriction_a.to_json_dict(),
            "restriction_b": self.restriction_b.to_json_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "Overlap":
        return cls(
            id=str(data["id"]),
            patch_a=str(data["patch_a"]),
            patch_b=str(data["patch_b"]),
            shared_domain=list(data.get("shared_domain", [])),
            restriction_a=RestrictionMap.from_json_dict(dict(data["restriction_a"])),
            restriction_b=RestrictionMap.from_json_dict(dict(data["restriction_b"])),
            metadata=dict(data.get("metadata", {})),
        )
