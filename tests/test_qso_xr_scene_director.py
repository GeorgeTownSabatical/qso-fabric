from __future__ import annotations

from pathlib import Path

from qso_xr.runtime import QSOXRRuntime


def test_scene_director_proposals_are_deterministic_and_non_mutating(tmp_path: Path) -> None:
    runtime = QSOXRRuntime(
        world_uri="qso://xr.world/director-test",
        knowledge_state_dir=tmp_path / "knowledge_director",
    )
    before_nodes = runtime.scene_graph.nodes_by_uri

    first = runtime.propose_scene_direction(
        objective="preserve topology legend readability with fixed camera",
        profile="analytic_educational",
    )
    second = runtime.propose_scene_direction(
        objective="preserve topology legend readability with fixed camera",
        profile="analytic_educational",
    )

    assert first == second
    assert first["direct_mutation_allowed"] is False
    assert runtime.scene_graph.nodes_by_uri == before_nodes
