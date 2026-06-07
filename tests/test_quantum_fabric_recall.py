from __future__ import annotations

from services.quantum.fabric import Overlap, Patch, QSOFabric, QuantumStateObject, RestrictionMap, score_coherent_recall


def test_coherent_recall_prefers_lower_obstruction_over_raw_similarity() -> None:
    fabric = QSOFabric(id="fabric.recall")
    query = QuantumStateObject(id="query", vector=[1 + 0j, 0j])
    high_raw = Patch(
        id="patch.high_raw",
        domain="memory",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(
            id="state.high_raw",
            vector=[1 + 0j, 0j],
            metadata={"continuity_role": "memory"},
        ),
    )
    coherent = Patch(
        id="patch.coherent",
        domain="memory",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(
            id="state.coherent",
            vector=[0.99 + 0j, 0.1 + 0j],
            metadata={"continuity_role": "memory"},
        ),
    )
    anchor = Patch(
        id="patch.anchor",
        domain="intent",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(id="state.anchor", vector=[0.99 + 0j, 0.1 + 0j]),
    )
    fabric.add_patch(high_raw)
    fabric.add_patch(coherent)
    fabric.add_patch(anchor)
    fabric.add_overlap(_identity_overlap("overlap.high_raw_anchor", high_raw.id, anchor.id))
    fabric.add_overlap(_identity_overlap("overlap.coherent_anchor", coherent.id, anchor.id))

    report = score_coherent_recall(fabric, query)
    results = report["results"]

    assert results[0]["patch_id"] == "patch.coherent"
    high_raw_result = next(item for item in results if item["patch_id"] == "patch.high_raw")
    coherent_result = next(item for item in results if item["patch_id"] == "patch.coherent")
    assert high_raw_result["local_similarity"] > coherent_result["local_similarity"]
    assert high_raw_result["obstruction_score"] > coherent_result["obstruction_score"]
    assert report["global_coherence"] < 1.0


def test_coherent_recall_includes_child_fabric_uri_and_depth_penalty() -> None:
    fabric = QSOFabric(id="fabric.recall.child")
    query = QuantumStateObject(id="query", vector=[1 + 0j, 0j])
    local = Patch(
        id="patch.local",
        domain="memory",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(id="state.local", vector=[1 + 0j, 0j], metadata={"continuity_role": "memory"}),
    )
    child = Patch(
        id="patch.child",
        domain="projection",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(
            id="state.child",
            vector=[1 + 0j, 0j],
            metadata={
                "child_fabric_uri": "qso://quantum.fabric/child",
                "continuity_role": "projection",
                "retrieval_weight": 1.0,
            },
        ),
    )
    fabric.add_patch(local)
    fabric.add_patch(child)

    report = score_coherent_recall(fabric, query, traversal_depths={"patch.child": 2})
    child_result = next(item for item in report["results"] if item["patch_id"] == "patch.child")

    assert report["results"][0]["patch_id"] == "patch.local"
    assert child_result["child_fabric_uri"] == "qso://quantum.fabric/child"
    assert child_result["traversal_depth"] == 2


def _identity_overlap(overlap_id: str, patch_a: str, patch_b: str) -> Overlap:
    return Overlap(
        id=overlap_id,
        patch_a=patch_a,
        patch_b=patch_b,
        shared_domain=["shared"],
        restriction_a=RestrictionMap(id=f"{overlap_id}.a", source_patch=patch_a, target_patch=overlap_id, projection=[[1 + 0j, 0j], [0j, 1 + 0j]]),
        restriction_b=RestrictionMap(id=f"{overlap_id}.b", source_patch=patch_b, target_patch=overlap_id, projection=[[1 + 0j, 0j], [0j, 1 + 0j]]),
    )
