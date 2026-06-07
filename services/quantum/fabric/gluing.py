"""Deterministic local-to-global coherence diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Any

from services.quantum.fabric.fabric import QSOFabric


@dataclass(slots=True)
class GluingEngine:
    """Compare overlap sections and compute obstruction/coherence diagnostics."""

    coherence_threshold: float = 0.8

    def analyze(self, fabric: QSOFabric) -> dict[str, Any]:
        pair_reports = []
        total_mismatch = 0.0
        for overlap_id, overlap in sorted(fabric.overlaps.items()):
            patch_a = fabric.get_patch(overlap.patch_a)
            patch_b = fabric.get_patch(overlap.patch_b)
            mismatch = overlap.mismatch(patch_a, patch_b)
            fidelity = overlap.fidelity(patch_a, patch_b)
            coherence = exp(-mismatch)
            total_mismatch += mismatch
            pair_reports.append(
                {
                    "overlap_id": overlap_id,
                    "patch_a": patch_a.id,
                    "patch_b": patch_b.id,
                    "shared_domain": list(overlap.shared_domain),
                    "mismatch": mismatch,
                    "fidelity": fidelity,
                    "coherence": coherence,
                }
            )
        global_coherence = exp(-total_mismatch)
        return {
            "fabric_id": fabric.id,
            "patch_count": len(fabric.patches),
            "overlap_count": len(fabric.overlaps),
            "total_overlap_mismatch": total_mismatch,
            "global_coherence": global_coherence,
            "healthy": global_coherence >= self.coherence_threshold,
            "obstruction_score": total_mismatch,
            "adjacency": fabric.adjacency(),
            "pairs": pair_reports,
        }
