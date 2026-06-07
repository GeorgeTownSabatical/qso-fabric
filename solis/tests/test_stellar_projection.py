from __future__ import annotations

from solis.config import SolisConfig
from solis.projectors.stellar_projector_v1 import StellarState, project_stellar_v1
from solis.services.solis_star_service import SolisStarService


def test_projection_invariance() -> None:
    state = StellarState(
        star_id="spherechain",
        chain_id="spherechain",
        mass=1.0,
        luminosity=1.0,
        core_temp=1.0,
        magnetic_field=0.9,
        entropy_index=0.1,
        fusion_rate=1.0,
        collapse_probability=0.0,
    )
    delta = {"mass": 0.25, "luminosity": 0.4, "entropy_index": 0.03, "magnetic_field": -0.01}

    a = project_stellar_v1(state, delta)
    b = project_stellar_v1(state, delta)

    assert a == b


def test_projection_boundary_normalizes_scientific_and_tiny_inputs() -> None:
    state = StellarState(
        star_id="spherechain",
        chain_id="spherechain",
        mass=1.0,
        luminosity=1.0,
        core_temp=1.0,
        magnetic_field=0.9,
        entropy_index=0.1,
        fusion_rate=1.0,
        collapse_probability=0.0,
    )

    scientific = project_stellar_v1(
        state,
        {
            "mass": "2.5e-1",
            "luminosity": "4e-1",
            "entropy_index": "3e-2",
            "magnetic_field": "-1e-2",
        },
    )
    decimal = project_stellar_v1(
        state,
        {"mass": 0.25, "luminosity": 0.4, "entropy_index": 0.03, "magnetic_field": -0.01},
    )
    assert scientific == decimal

    tiny = project_stellar_v1(
        state,
        {
            "mass": "1e-24",
            "luminosity": "1e-24",
            "entropy_index": "1e-24",
            "magnetic_field": "1e-24",
        },
    )
    zero = project_stellar_v1(
        state,
        {"mass": 0.0, "luminosity": 0.0, "entropy_index": 0.0, "magnetic_field": 0.0},
    )
    assert tiny == zero


def test_deterministic_replay_consistency() -> None:
    config = SolisConfig(anchor_interval=4)
    node_a = SolisStarService(config=config)
    node_b = SolisStarService(config=config)

    node_a.create_star(star_id="spherechain", chain_id="spherechain")
    node_b.create_star(star_id="spherechain", chain_id="spherechain")

    deltas = [
        {"mass": 0.5, "luminosity": 0.8, "entropy_index": 0.02, "magnetic_field": -0.01},
        {"mass": 0.2, "luminosity": 0.3, "entropy_index": 0.01, "magnetic_field": -0.02},
        {"mass": 0.1, "luminosity": 0.2, "entropy_index": 0.03, "magnetic_field": -0.01},
    ]

    for delta in deltas:
        node_a.patch_star(star_uri_or_id="spherechain", delta=delta, actor="deterministic")
        node_b.patch_star(star_uri_or_id="spherechain", delta=delta, actor="deterministic")

    state_a = node_a.get_star("spherechain")["state_layer"]
    state_b = node_b.get_star("spherechain")["state_layer"]

    assert state_a == state_b
    assert node_a.merkle_anchor.root() == node_b.merkle_anchor.root()
