from __future__ import annotations

from services.quantum.fabric import QuantumStateObject


def test_quantum_state_object_normalizes_and_round_trips() -> None:
    state = QuantumStateObject(id="s1", vector=[3 + 0j, 4 + 0j], phase=0.2)
    assert state.dimension == 2
    assert abs(state.norm() - 1.0) < 1e-9
    restored = QuantumStateObject.from_json_dict(state.to_json_dict())
    assert restored.id == "s1"
    assert restored.vector == state.vector


def test_quantum_state_object_fidelity_is_one_for_identical_states() -> None:
    left = QuantumStateObject(id="left", vector=[1 + 0j, 1 + 0j])
    right = QuantumStateObject(id="right", vector=[2 + 0j, 2 + 0j])
    assert abs(left.fidelity_with(right) - 1.0) < 1e-9
