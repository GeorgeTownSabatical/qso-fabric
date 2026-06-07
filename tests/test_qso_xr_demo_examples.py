from __future__ import annotations

from pathlib import Path

from qso_xr.demo_examples import get_demo_example, list_demo_examples
from qso_xr.runtime import QSOXRRuntime


def test_qso_xr_demo_examples_include_two_distinct_image_profiles() -> None:
    names = list_demo_examples()
    assert names == ["image_1_shadow_throne", "image_2_torus_topology"]

    first = get_demo_example("image_1_shadow_throne")
    second = get_demo_example("image_2_torus_topology")
    assert first["profile"] != second["profile"]
    assert len(first["distinct_needs"]) >= 3
    assert len(second["distinct_needs"]) >= 3


def test_qso_xr_runtime_can_seed_both_image_demos(tmp_path: Path) -> None:
    runtime = QSOXRRuntime(
        world_uri="qso://xr.world/image-demos",
        knowledge_state_dir=tmp_path / "knowledge",
    )
    seeded_1 = runtime.apply_demo_example("image_1_shadow_throne")
    seeded_2 = runtime.apply_demo_example("image_2_torus_topology")

    assert seeded_1["seeded_nodes"] >= 3
    assert seeded_2["seeded_nodes"] >= 3
    assert seeded_1["render_stats"]["visible"] >= 1
    assert seeded_2["render_stats"]["visible"] >= 1
