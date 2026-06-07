from __future__ import annotations

from qso_vr_visualization.scene_render_projector import SceneRenderProjector


def _find_visible(payload: dict, uri: str) -> dict:
    for row in payload.get("visible", []):
        if row.get("uri") == uri:
            return row
    raise KeyError(uri)


def test_scene_render_projector_world_matrix_propagation() -> None:
    world_uri = "qso://vr.world/demo"
    root_uri = f"{world_uri}/node/root"
    child_uri = f"{world_uri}/node/child"

    projector = SceneRenderProjector()
    payload = projector.project(
        world_uri=world_uri,
        frame=42,
        viewpoint={"center": [0, 0, 0], "radius": 200, "layer_mask": 1},
        nodes_by_uri={
            root_uri: {
                "id": "root",
                "parent": None,
                "transform": {"pos": [1, 0, 0], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
                "bounds": {"type": "aabb", "min": [-1, -1, -1], "max": [1, 1, 1]},
                "layer_mask": 1,
            },
            child_uri: {
                "id": "child",
                "parent": root_uri,
                "transform": {"pos": [0, 2, 0], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
                "bounds": {"type": "aabb", "min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]},
                "layer_mask": 1,
            },
        },
    )

    child = _find_visible(payload, child_uri)
    world_matrix = child["world_matrix"]
    assert world_matrix[3] == 1.0
    assert world_matrix[7] == 2.0
    assert world_matrix[11] == 0.0
    assert payload["frame"] == 42
    assert payload["stats"]["visible"] == 2


def test_scene_render_projector_bounds_culling_and_determinism() -> None:
    world_uri = "qso://vr.world/demo"
    near_uri = f"{world_uri}/node/near"
    far_uri = f"{world_uri}/node/far"

    projector = SceneRenderProjector()
    nodes = {
        near_uri: {
            "id": "near",
            "transform": {"pos": [2, 0, 0], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
            "bounds": {"type": "aabb", "min": [-1, -1, -1], "max": [1, 1, 1]},
            "layer_mask": 1,
        },
        far_uri: {
            "id": "far",
            "transform": {"pos": [120, 0, 0], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
            "bounds": {"type": "aabb", "min": [-1, -1, -1], "max": [1, 1, 1]},
            "layer_mask": 1,
        },
    }
    viewpoint = {"center": [0, 0, 0], "radius": 25, "layer_mask": 1}

    first = projector.project(world_uri=world_uri, nodes_by_uri=nodes, viewpoint=viewpoint, frame=1)
    second = projector.project(world_uri=world_uri, nodes_by_uri=nodes, viewpoint=viewpoint, frame=1)

    assert [row["uri"] for row in first["visible"]] == [near_uri]
    assert first["stats"]["culled"] == 1
    assert first["stats"]["visible"] == 1
    assert first == second


def test_scene_render_projector_reports_integrity_issues() -> None:
    world_uri = "qso://vr.world/demo"
    a_uri = f"{world_uri}/node/a"
    b_uri = f"{world_uri}/node/b"

    projector = SceneRenderProjector()
    payload = projector.project(
        world_uri=world_uri,
        nodes_by_uri={
            a_uri: {
                "id": "dup",
                "parent": b_uri,
                "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
            },
            b_uri: {
                "id": "dup",
                "parent": a_uri,
                "transform": {"pos": [1, 0, 0], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
            },
        },
    )
    issues = payload["integrity"]["issues"]
    types = {row["type"] for row in issues}
    assert payload["integrity"]["ok"] is False
    assert "parent_cycle" in types
    assert "duplicate_node_id" in types
