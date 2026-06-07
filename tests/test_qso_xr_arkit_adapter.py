from __future__ import annotations

from pathlib import Path

from qso_xr.arkit_adapter import ARKitAdapter
from qso_xr.package_registry import coverage_summary
from qso_xr.runtime import QSOXRRuntime


def _sample_arkit_frame() -> dict:
    return {
        "session_id": "arkit-session-01",
        "timestamp_ms": 1700000000,
        "camera": {
            "tracking_state": "normal",
            "exposure": 0.42,
            "transform": {"position": [0.0, 1.7, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0]},
        },
        "anchors": [
            {
                "anchor_id": "plane_floor",
                "classification": "floor",
                "tracking_state": "mapped",
                "transform": {
                    "position": [0.0, 0.0, -1.3],
                    "rotation": [0.0, 0.0, 0.0, 1.0],
                    "scale": [1.0, 1.0, 1.0],
                },
                "extent": [2.0, 0.1, 2.0],
            },
            {
                "anchor_id": "table_top",
                "classification": "table",
                "tracking_state": "mapped",
                "transform": {
                    "position": [0.7, 0.75, -0.9],
                    "rotation": [0.0, 0.0, 0.0, 1.0],
                    "scale": [1.0, 1.0, 1.0],
                },
                "extent": [1.1, 0.08, 0.7],
            },
        ],
    }


def test_arkit_adapter_import_export_roundtrip_is_deterministic() -> None:
    adapter = ARKitAdapter()
    frame = _sample_arkit_frame()
    first = adapter.roundtrip(world_uri="qso://xr.world.arkit.test", frame=frame)
    second = adapter.roundtrip(world_uri="qso://xr.world.arkit.test", frame=frame)
    assert first == second
    assert first["anchor_count_in"] == 2
    assert first["anchor_count_out"] == 2


def test_runtime_arkit_import_and_export_path(tmp_path: Path) -> None:
    runtime = QSOXRRuntime(
        world_uri="qso://xr.world.arkit.runtime",
        knowledge_state_dir=tmp_path / "arkit_knowledge",
    )
    out = runtime.import_arkit_frame(_sample_arkit_frame())
    assert out["nodes_written"] >= 3  # 2 anchors + 1 camera
    assert out["frame_hash"]

    exported = runtime.export_arkit_scene()
    assert exported["world_uri"] == "qso://xr.world.arkit.runtime"
    assert len(exported["anchors"]) == 2


def test_package_registry_marks_arkit_adapter_implemented() -> None:
    summary = coverage_summary()
    assert "qso-apple-arkit-adapter" in summary["implemented_packages"]
