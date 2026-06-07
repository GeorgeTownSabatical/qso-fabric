from __future__ import annotations

from services.quantum.fabric import GluingEngine, Overlap, Patch, QSOFabric, QuantumStateObject, RestrictionMap


def test_gluing_engine_reports_high_coherence_for_compatible_patches() -> None:
    fabric = QSOFabric(id="fabric.test")
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
        state=QuantumStateObject(id="state.b", vector=[1 + 0j, 1.01 + 0j]),
    )
    fabric.add_patch(patch_a)
    fabric.add_patch(patch_b)
    fabric.add_overlap(
        Overlap(
            id="o1",
            patch_a=patch_a.id,
            patch_b=patch_b.id,
            shared_domain=["shared"],
            restriction_a=RestrictionMap(id="ra", source_patch=patch_a.id, target_patch="ov", projection=[[1 + 0j, 0j], [0j, 1 + 0j]]),
            restriction_b=RestrictionMap(id="rb", source_patch=patch_b.id, target_patch="ov", projection=[[1 + 0j, 0j], [0j, 1 + 0j]]),
        )
    )
    report = GluingEngine(coherence_threshold=0.95).analyze(fabric)
    assert report["healthy"] is True
    assert report["global_coherence"] > 0.99
    assert report["adjacency"] == {"patch.a": ["patch.b"], "patch.b": ["patch.a"]}
