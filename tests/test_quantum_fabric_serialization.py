from __future__ import annotations

from services.quantum.fabric import Overlap, Patch, QSOFabric, QuantumStateObject, RestrictionMap


def test_qso_fabric_round_trip_preserves_patches_and_overlaps() -> None:
    fabric = QSOFabric(id="fabric.serialize")
    patch_a = Patch(
        id="patch.a",
        domain="a",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(id="state.a", vector=[1 + 0j, 0j]),
    )
    patch_b = Patch(
        id="patch.b",
        domain="b",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(id="state.b", vector=[0j, 1 + 0j]),
    )
    fabric.add_patch(patch_a)
    fabric.add_patch(patch_b)
    fabric.add_overlap(
        Overlap(
            id="o1",
            patch_a="patch.a",
            patch_b="patch.b",
            shared_domain=["shared"],
            restriction_a=RestrictionMap(id="ra", source_patch="patch.a", target_patch="ov", projection=[[1 + 0j, 0j], [0j, 1 + 0j]]),
            restriction_b=RestrictionMap(id="rb", source_patch="patch.b", target_patch="ov", projection=[[1 + 0j, 0j], [0j, 1 + 0j]]),
        )
    )
    restored = QSOFabric.from_json_dict(fabric.to_json_dict())
    assert sorted(restored.patches) == ["patch.a", "patch.b"]
    assert sorted(restored.overlaps) == ["o1"]
