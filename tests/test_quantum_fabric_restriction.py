from __future__ import annotations

from services.quantum.fabric import QuantumStateObject, RestrictionMap


def test_restriction_map_applies_linear_projection() -> None:
    state = QuantumStateObject(id="state.src", vector=[1 + 0j, 0j])
    restriction = RestrictionMap(
        id="r1",
        source_patch="patch.src",
        target_patch="overlap.1",
        projection=[[1 + 0j, 0j]],
    )
    projected = restriction.apply(state)
    assert projected.dimension == 1
    assert projected.vector == (1 + 0j,)
