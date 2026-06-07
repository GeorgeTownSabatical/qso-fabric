"""Deterministic two-patch demo for the quantum fabric kernel."""

from __future__ import annotations

import json

from services.quantum.fabric import GluingEngine, Overlap, Patch, QSOFabric, QuantumStateObject, RestrictionMap


def build_demo_report() -> dict[str, object]:
    patch_a = Patch(
        id="patch.alpha",
        domain="sensor.alpha",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(id="state.alpha", vector=[1 + 0j, 1 + 0j]),
    )
    patch_b = Patch(
        id="patch.beta",
        domain="sensor.beta",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(id="state.beta", vector=[0.99 + 0j, 1.01 + 0j]),
    )
    overlap = Overlap(
        id="overlap.alpha_beta",
        patch_a=patch_a.id,
        patch_b=patch_b.id,
        shared_domain=["shared.coherence.window"],
        restriction_a=RestrictionMap(
            id="restrict.alpha",
            source_patch=patch_a.id,
            target_patch="overlap.alpha_beta",
            projection=[[1 + 0j, 0j], [0j, 1 + 0j]],
        ),
        restriction_b=RestrictionMap(
            id="restrict.beta",
            source_patch=patch_b.id,
            target_patch="overlap.alpha_beta",
            projection=[[1 + 0j, 0j], [0j, 1 + 0j]],
        ),
    )
    fabric = QSOFabric(id="fabric.demo")
    fabric.add_patch(patch_a)
    fabric.add_patch(patch_b)
    fabric.add_overlap(overlap)
    return GluingEngine(coherence_threshold=0.95).analyze(fabric)


def main() -> None:
    print(json.dumps(build_demo_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
