from __future__ import annotations

from solis.physics.contagion_engine import contagion_index, exposure_matrix, snapshot
from solis.physics.fixed_math import Fixed64
from solis.physics.sheaf_model import influence_matrix, make_sheaf_state, propagate
from solis.physics.stability_solver import solve_stability_field
from solis.shared.hashing import sha256_hex_obj


def test_contagion_snapshot_deterministic() -> None:
    collapse = {
        "qso://solis.star.a": Fixed64.from_str("0.2"),
        "qso://solis.star.b": Fixed64.from_str("0.4"),
    }
    first = snapshot(collapse)
    second = snapshot(collapse)

    assert first == second
    assert first.contagion_index >= Fixed64.zero()
    assert first.contagion_index <= Fixed64.one()
    assert sha256_hex_obj({"idx": first.contagion_index.to_raw()}) == sha256_hex_obj({"idx": second.contagion_index.to_raw()})


def test_sheaf_propagation_stable() -> None:
    sheaf = make_sheaf_state(
        {
            "liquidity": {"x": Fixed64.from_str("1.0")},
            "governance": {"x": Fixed64.from_str("0.5")},
        }
    )
    inf = influence_matrix(sheaf)
    projected = propagate(sheaf, inf)

    assert len(projected.layers) == 2
    by_name = {layer.name: layer.field for layer in projected.layers}
    assert by_name["liquidity"]["x"] >= Fixed64.from_str("1.0")
    assert by_name["governance"]["x"] >= Fixed64.from_str("0.5")


def test_stability_solver_outputs_bounded_indices() -> None:
    state = {
        "qso://solis.star.a": {
            "entropy_index": Fixed64.from_str("0.2"),
            "previous_entropy_index": Fixed64.from_str("0.1"),
            "magnetic_field": Fixed64.from_str("0.8"),
            "fusion_rate": Fixed64.from_str("0.9"),
        },
        "qso://solis.star.b": {
            "entropy_index": Fixed64.from_str("0.4"),
            "previous_entropy_index": Fixed64.from_str("0.3"),
            "magnetic_field": Fixed64.from_str("0.6"),
            "fusion_rate": Fixed64.from_str("1.0"),
        },
    }

    out = solve_stability_field(state)

    assert out.systemic_risk_index >= Fixed64.zero()
    assert out.systemic_risk_index <= Fixed64.one()
    assert out.stability_margin >= Fixed64.zero()
    assert out.stability_margin <= Fixed64.one()
    assert sorted(out.collapse_vector.keys()) == sorted(state.keys())
    assert sorted(out.entropy_gradient.keys()) == sorted(state.keys())


def test_contagion_index_direct() -> None:
    collapse = {
        "a": Fixed64.from_str("0.25"),
        "b": Fixed64.from_str("0.75"),
    }
    matrix = exposure_matrix(["a", "b"])
    idx = contagion_index(collapse, matrix)
    assert idx >= Fixed64.zero()
    assert idx <= Fixed64.one()
