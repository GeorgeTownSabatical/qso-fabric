from __future__ import annotations

from pathlib import Path

import pytest

from qso_xr.knowledge_lattice import ConsistencyConflict
from qso_xr.runtime import QSOXRRuntime


def test_qso_xr_runtime_scene_projection_and_entanglement(tmp_path: Path) -> None:
    world_uri = "qso://xr.world/runtime"
    runtime = QSOXRRuntime(world_uri=world_uri, knowledge_state_dir=tmp_path / "knowledge_runtime")

    root_uri = f"{world_uri}/node/root"
    mirror_uri = f"{world_uri}/node/mirror"
    runtime.entanglement.entangle(root_uri, mirror_uri, "mirrors", strength=0.5, bidirectional=False)

    out = runtime.upsert_world_node(
        root_uri,
        {
            "id": "root",
            "transform": {"pos": [2, 0, 0], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
            "bounds": {"min": [-1, -1, -1], "max": [1, 1, 1]},
            "mass": 4.0,
        },
    )
    assert out["entangled_emissions"] == 1

    drained = runtime.stream_projection.drain()
    assert len(drained) == 2
    assert drained[0]["uri"] == root_uri
    assert drained[1]["uri"] == mirror_uri
    assert drained[1]["render_delta"]["global"]["mass"] == 2.0

    projection = runtime.render_scene(viewpoint={"center": [0, 0, 0], "radius": 100})
    assert projection["stats"]["visible"] == 1
    assert projection["visible"][0]["uri"] == root_uri

    status = runtime.status()
    assert status["package_coverage"]["total_packages"] == 32


def test_qso_xr_runtime_physics_tick_is_deterministic(tmp_path: Path) -> None:
    world_uri = "qso://xr.world/physics"
    runtime_a = QSOXRRuntime(world_uri=world_uri, knowledge_state_dir=tmp_path / "knowledge_physics_a")
    runtime_b = QSOXRRuntime(world_uri=world_uri, knowledge_state_dir=tmp_path / "knowledge_physics_b")

    for runtime in (runtime_a, runtime_b):
        runtime.physics_engine.add_body("a", position=[0, 0, 0], velocity=[0, 0, 0], mass=1.0, radius=0.5)
        runtime.physics_engine.apply_impulse("a", [1.0, 0.0, 0.0])

    event_a = runtime_a.tick_physics(dt_ms=20.0, gravity=[0.0, 0.0, 0.0])
    event_b = runtime_b.tick_physics(dt_ms=20.0, gravity=[0.0, 0.0, 0.0])
    assert event_a == event_b


def test_qso_xr_runtime_profile_gate_blocks_low_confidence_analytic_claims(tmp_path: Path) -> None:
    runtime = QSOXRRuntime(world_uri="qso://xr.world/gate", knowledge_state_dir=tmp_path / "knowledge_gate")
    with pytest.raises(ConsistencyConflict):
        runtime.merge_knowledge(
            branch_name="analytic-gate",
            claims=[
                {
                    "section": "math.topology",
                    "claim_id": "gate-c1",
                    "statement": "low confidence analytic claim",
                    "confidence": 0.42,
                }
            ],
            vote_approved=True,
            profile="analytic_educational",
            enforce_profile_gate=True,
        )
