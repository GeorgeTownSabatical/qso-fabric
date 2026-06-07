"""Container graph for local quantum-inspired patch structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.overlap import Overlap
from services.quantum.fabric.patch import Patch


@dataclass(slots=True)
class QSOFabric:
    """Collection of patches and overlaps used by the gluing engine."""

    id: str
    patches: dict[str, Patch] = field(default_factory=dict)
    overlaps: dict[str, Overlap] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_patch(self, patch: Patch) -> None:
        if patch.id in self.patches:
            raise ValueError(f"patch already exists: {patch.id}")
        self.patches[patch.id] = patch

    def add_overlap(self, overlap: Overlap) -> None:
        if overlap.id in self.overlaps:
            raise ValueError(f"overlap already exists: {overlap.id}")
        if overlap.patch_a not in self.patches or overlap.patch_b not in self.patches:
            raise KeyError("overlap references unknown patch")
        self.overlaps[overlap.id] = overlap

    def get_patch(self, patch_id: str) -> Patch:
        return self.patches[patch_id]

    def adjacency(self) -> dict[str, list[str]]:
        graph = {patch_id: [] for patch_id in self.patches}
        for overlap in self.overlaps.values():
            graph.setdefault(overlap.patch_a, []).append(overlap.patch_b)
            graph.setdefault(overlap.patch_b, []).append(overlap.patch_a)
        for patch_id in graph:
            graph[patch_id] = sorted(set(graph[patch_id]))
        return graph

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "patches": {patch_id: patch.to_json_dict() for patch_id, patch in sorted(self.patches.items())},
            "overlaps": {overlap_id: overlap.to_json_dict() for overlap_id, overlap in sorted(self.overlaps.items())},
            "metadata": self.metadata,
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "QSOFabric":
        fabric = cls(id=str(data["id"]), metadata=dict(data.get("metadata", {})))
        for patch_payload in dict(data.get("patches", {})).values():
            fabric.add_patch(Patch.from_json_dict(dict(patch_payload)))
        for overlap_payload in dict(data.get("overlaps", {})).values():
            fabric.add_overlap(Overlap.from_json_dict(dict(overlap_payload)))
        return fabric
