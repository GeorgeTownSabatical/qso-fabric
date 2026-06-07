from __future__ import annotations

import pytest

from services.quantum.fabric import Patch, QuantumStateObject


def test_patch_requires_basis_dimension_match() -> None:
    with pytest.raises(ValueError):
        Patch(
            id="patch.bad",
            domain="demo",
            basis=["|0>", "|1>", "|2>"],
            state=QuantumStateObject(id="state.bad", vector=[1 + 0j, 0j]),
        )


def test_patch_round_trip() -> None:
    patch = Patch(
        id="patch.good",
        domain="demo",
        basis=["|0>", "|1>"],
        state=QuantumStateObject(id="state.good", vector=[1 + 0j, 0j]),
    )
    restored = Patch.from_json_dict(patch.to_json_dict())
    assert restored.id == patch.id
    assert restored.state.vector == patch.state.vector
