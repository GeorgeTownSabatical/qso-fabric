from __future__ import annotations

from pathlib import Path

from qso_xr.runtime import QSOXRRuntime


GOLDEN_HASHES = {
    "image_1_shadow_throne": "e7b4866c0617733812b1a0d89accaaa3bbc2d422fd4db5657e373207621a6655",
    "image_2_torus_topology": "d91a22c6717edce073ad7b88dd37fc3e927727ab8877dba869e69da56b2706b9",
}


def test_qso_xr_demo_frame_hashes_match_golden_values(tmp_path: Path) -> None:
    for example, expected_hash in GOLDEN_HASHES.items():
        runtime = QSOXRRuntime(
            world_uri=f"qso://xr.world.golden/{example}",
            knowledge_state_dir=tmp_path / f"knowledge_{example}",
        )
        seeded = runtime.apply_demo_example(example)
        assert seeded["frame_hash"] == expected_hash
