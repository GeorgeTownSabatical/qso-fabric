from __future__ import annotations

import asyncio
import json
from pathlib import Path

from api.mcp_tools.qso_tools import QSOMCPTools
from qso_xr.runtime import QSOXRRuntime
from tools.qso_web_api import QSOAPI, WebXRAdapter


def test_webxr_sse_projection_stream_emits_projection_packets() -> None:
    tools = QSOMCPTools()
    adapter = WebXRAdapter(tools)

    src = "qso://vr.world.webxr.city"
    dst = "qso://identity.user.webxr.viewer"
    tools.qso_create(src, {"type": "world"})
    tools.qso_create(dst, {"type": "identity"})
    tools.qso_entangle(src, dst, "feeds-view", bidirectional=False)

    async def scenario() -> None:
        stream = adapter.stream_projection_sse(
            uri=dst,
            viewpoint={"center": [0, 0, 0], "radius": 50},
        )
        consumer = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)

        tools.qso_patch(
            src,
            {"position": [3, 0, 0], "objects": {"cube": {"position": [3, 0, 0], "visible": True}}},
            actor="engine",
        )

        packet = await asyncio.wait_for(consumer, timeout=1.5)
        lines = [line for line in packet.strip().splitlines() if line]
        assert lines[0] == "event: projection"
        assert lines[1].startswith("data: ")

        payload = json.loads(lines[1][6:])
        assert payload["uri"] == src
        assert payload["render_delta"]["spatial"]["position"] == [3.0, 0.0, 0.0]
        assert "cursor_token" in payload

    asyncio.run(scenario())


def test_webxr_apply_action_set_pose_updates_state() -> None:
    tools = QSOMCPTools()
    adapter = WebXRAdapter(tools)
    uri = "qso://vr.world.webxr.avatar_scene"
    tools.qso_create(uri, {"type": "world"})

    out = adapter.apply_action(
        uri=uri,
        action={"type": "set_pose", "object_id": "avatar_01", "position": [1, 2, 3]},
        actor="viewer",
    )

    assert out["delta"]["objects"]["avatar_01"]["position"] == [1.0, 2.0, 3.0]
    state = tools.qso_read(uri)["state_layer"]
    assert state["objects"]["avatar_01"]["position"] == [1.0, 2.0, 3.0]


def test_qso_api_handles_webxr_action_route() -> None:
    tools = QSOMCPTools()
    api = QSOAPI(tools)
    uri = "qso://vr.world.webxr.api_route"
    tools.qso_create(uri, {"type": "world"})

    result = api.handle_request(
        {
            "route": "xr.apply_action",
            "uri": uri,
            "action": {"type": "patch", "delta": {"weather": {"rain": True}}},
            "actor": "ui",
        }
    )

    assert result["uri"] == uri
    assert result["delta"]["weather"]["rain"] is True
    state = tools.qso_read(uri)["state_layer"]
    assert state["weather"]["rain"] is True


def test_webxr_load_qff_is_passive_and_non_authoritative(tmp_path: Path) -> None:
    export_runtime = QSOXRRuntime(
        world_uri="qso://xr.world.demo.passive",
        knowledge_state_dir=tmp_path / "knowledge",
    )
    export_runtime.apply_demo_example("image_2_torus_topology")
    artifact = tmp_path / "demo_export.qff.json"
    export_runtime.export_qff(path=artifact, profile="analytic_educational")

    tools = QSOMCPTools()
    adapter = WebXRAdapter(tools)
    result = adapter.load_qff_scene(path=str(artifact), passive=True)

    assert result["mode"] == "passive"
    assert result["mutated_runtime"] is False
    assert result["event_count_before"] == result["event_count_after"]
    assert result["boot_payload"]["world_uri"] == "qso://xr.world.demo.passive"
    assert result["boot_payload"]["scene"]["node_count"] >= 3


def test_qso_api_handles_xr_load_qff_route(tmp_path: Path) -> None:
    export_runtime = QSOXRRuntime(
        world_uri="qso://xr.world.demo.route",
        knowledge_state_dir=tmp_path / "knowledge_route",
    )
    export_runtime.apply_demo_example("image_1_shadow_throne")
    artifact = tmp_path / "route_export.qff.json"
    export_runtime.export_qff(path=artifact, profile="cinematic_low_light")

    api = QSOAPI(QSOMCPTools())
    out = api.handle_request({"route": "xr.load_qff", "path": str(artifact), "passive": True})
    assert out["mode"] == "passive"
    assert out["mutated_runtime"] is False
    assert out["boot_payload"]["world_uri"] == "qso://xr.world.demo.route"
