from __future__ import annotations

from services.quantum.fabric import CONTINUITY_METADATA_KEYS, QuantumStateObject


def test_quantum_state_object_normalizes_and_round_trips() -> None:
    state = QuantumStateObject(id="s1", vector=[3 + 0j, 4 + 0j], phase=0.2)
    assert state.dimension == 2
    assert abs(state.norm() - 1.0) < 1e-9
    restored = QuantumStateObject.from_json_dict(state.to_json_dict())
    assert restored.id == "s1"
    assert restored.vector == state.vector


def test_quantum_state_object_preserves_continuity_metadata_round_trip() -> None:
    metadata = {
        "parent_state_id": "state.parent",
        "child_fabric_uri": "qso://quantum.fabric/child",
        "continuity_role": "memory",
        "retrieval_weight": 1.25,
        "projection_horizon": "next-session",
        "provenance_refs": ["event.1"],
        "contradiction_refs": ["contradiction.1"],
        "repair_history_refs": ["repair.1"],
        "unrelated": {"preserved": True},
    }
    state = QuantumStateObject(id="state.child", vector=[1 + 0j, 0j], metadata=metadata)

    restored = QuantumStateObject.from_json_dict(state.to_json_dict())

    assert set(CONTINUITY_METADATA_KEYS).issubset(restored.metadata)
    assert restored.metadata == metadata
    assert restored.continuity_metadata() == {key: metadata[key] for key in CONTINUITY_METADATA_KEYS}
    assert restored.parent_state_id == "state.parent"
    assert restored.child_fabric_uri == "qso://quantum.fabric/child"
    assert restored.continuity_role == "memory"
    assert restored.retrieval_weight == 1.25


def test_quantum_state_object_fidelity_is_one_for_identical_states() -> None:
    left = QuantumStateObject(id="left", vector=[1 + 0j, 1 + 0j])
    right = QuantumStateObject(id="right", vector=[2 + 0j, 2 + 0j])
    assert abs(left.fidelity_with(right) - 1.0) < 1e-9
