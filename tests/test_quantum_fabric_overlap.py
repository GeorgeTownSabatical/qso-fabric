from __future__ import annotations

from services.quantum.fabric import Overlap, Patch, QuantumStateObject, RestrictionMap


def test_overlap_metrics_reflect_close_states() -> None:
    patch_a = Patch(
        id="patch.a",
        domain="a",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(id="state.a", vector=[1 + 0j, 1 + 0j]),
    )
    patch_b = Patch(
        id="patch.b",
        domain="b",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(id="state.b", vector=[1 + 0j, 0.98 + 0j]),
    )
    overlap = Overlap(
        id="o1",
        patch_a="patch.a",
        patch_b="patch.b",
        shared_domain=["shared"],
        restriction_a=RestrictionMap(id="ra", source_patch="patch.a", target_patch="ov", projection=[[1 + 0j, 0j], [0j, 1 + 0j]]),
        restriction_b=RestrictionMap(id="rb", source_patch="patch.b", target_patch="ov", projection=[[1 + 0j, 0j], [0j, 1 + 0j]]),
    )
    assert overlap.mismatch(patch_a, patch_b) < 0.02
    assert overlap.fidelity(patch_a, patch_b) > 0.999
