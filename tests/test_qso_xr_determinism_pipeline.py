from __future__ import annotations

from pathlib import Path

from qso_xr.qff_exporter import load_qff_json
from qso_xr.runtime import QSOXRRuntime


def test_demo_shadow_throne_determinism(tmp_path: Path) -> None:
    rt = QSOXRRuntime(
        world_uri="qso://xr.world/test",
        knowledge_state_dir=tmp_path / "knowledge_det",
    )
    out1 = rt.apply_demo_example("image_1_shadow_throne")
    out2 = rt.apply_demo_example("image_1_shadow_throne")

    assert out1["frame_hash"] == out2["frame_hash"]


def test_qff_export_contains_scene_knowledge_and_frame_hash(tmp_path: Path) -> None:
    rt = QSOXRRuntime(
        world_uri="qso://xr.world/qff",
        knowledge_state_dir=tmp_path / "knowledge_qff",
    )
    rt.apply_demo_example("image_2_torus_topology")
    artifact = tmp_path / "out.qff.json"
    result = rt.export_qff(path=artifact, profile="analytic_educational")

    payload = load_qff_json(artifact)
    assert payload["scene"]["node_count"] >= 3
    assert payload["knowledge"]["claim_count"] >= 2
    assert payload["render"]["frame_hash"] == result["frame_hash"]
    assert payload["state_hash"] == result["state_hash"]
