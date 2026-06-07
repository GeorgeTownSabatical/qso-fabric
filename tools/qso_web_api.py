from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncIterator, Dict

from api.mcp_tools.qso_tools import QSOMCPTools
from qso_xr.qff_exporter import load_qff_json


def _is_vec3(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 3 and all(isinstance(v, (int, float)) for v in value)


class WebXRAdapter:
    def __init__(self, tools: QSOMCPTools | None = None) -> None:
        self.tools = tools or QSOMCPTools()

    async def stream_projection_sse(
        self,
        uri: str,
        viewpoint: Dict[str, Any] | None = None,
        radius: float = 150.0,
        cursor: int | str | None = None,
        backpressure: str = "drop_oldest",
        queue_size: int = 256,
        strict: bool = True,
    ) -> AsyncIterator[str]:
        stream = self.tools.qso_subscribe_projection(
            uri=uri,
            viewpoint=viewpoint,
            radius=radius,
            cursor=cursor,
            backpressure=backpressure,
            queue_size=queue_size,
            strict=strict,
        )
        async for projection in stream:
            yield self._to_sse(event="projection", payload=projection)

    async def stream_projection_ws(
        self,
        uri: str,
        viewpoint: Dict[str, Any] | None = None,
        radius: float = 150.0,
        cursor: int | str | None = None,
        backpressure: str = "drop_oldest",
        queue_size: int = 256,
        strict: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        stream = self.tools.qso_subscribe_projection(
            uri=uri,
            viewpoint=viewpoint,
            radius=radius,
            cursor=cursor,
            backpressure=backpressure,
            queue_size=queue_size,
            strict=strict,
        )
        async for projection in stream:
            yield {"type": "projection", "payload": projection}

    def apply_action(
        self,
        *,
        uri: str,
        action: Dict[str, Any],
        actor: str = "webxr-client",
        policy_version: str = "v1",
        node_id: str = "webxr",
    ) -> Dict[str, Any]:
        delta = self._action_to_delta(action)
        event = self.tools.qso_patch(
            uri=uri,
            delta=delta,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        return {"uri": uri, "delta": delta, "event": event}

    def load_qff_scene(self, *, path: str, passive: bool = True) -> Dict[str, Any]:
        if not passive:
            raise ValueError("WebXR QFF loader supports passive boot only")
        snapshot = load_qff_json(Path(path))
        world_uri = str(snapshot.get("world_uri", ""))
        before = self._timeline_len(world_uri) if world_uri else 0

        boot_payload = {
            "world_uri": world_uri,
            "profile": snapshot.get("profile", "default"),
            "state_hash": snapshot.get("state_hash", ""),
            "scene": snapshot.get("scene", {}),
            "knowledge": snapshot.get("knowledge", {}),
            "render": snapshot.get("render", {}),
        }

        after = self._timeline_len(world_uri) if world_uri else 0
        return {
            "mode": "passive",
            "mutated_runtime": after != before,
            "event_count_before": before,
            "event_count_after": after,
            "boot_payload": boot_payload,
        }

    @staticmethod
    def _action_to_delta(action: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(action, dict):
            raise ValueError("action must be an object")

        action_type = str(action.get("type", "patch"))
        if action_type == "patch":
            payload = action.get("delta")
            if not isinstance(payload, dict):
                raise ValueError("patch action requires object field 'delta'")
            return payload

        if action_type == "set_pose":
            object_id = str(action.get("object_id", "")).strip()
            if not object_id:
                raise ValueError("set_pose action requires non-empty object_id")

            patch: Dict[str, Any] = {}
            if "position" in action:
                if not _is_vec3(action["position"]):
                    raise ValueError("set_pose position must be vec3")
                patch["position"] = [float(v) for v in action["position"]]
            if "rotation" in action:
                if not _is_vec3(action["rotation"]):
                    raise ValueError("set_pose rotation must be vec3")
                patch["rotation"] = [float(v) for v in action["rotation"]]
            if not patch:
                raise ValueError("set_pose requires at least one of position or rotation")
            return {"objects": {object_id: patch}}

        raise ValueError(f"unsupported action type: {action_type}")

    @staticmethod
    def _to_sse(event: str, payload: Dict[str, Any]) -> str:
        data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"event: {event}\ndata: {data}\n\n"

    def _timeline_len(self, uri: str) -> int:
        if not uri:
            return 0
        try:
            return len(self.tools.runtime.event_log.timeline(uri))
        except Exception:
            return 0


class QSOAPI:
    def __init__(self, tools: QSOMCPTools | None = None) -> None:
        self.tools = tools or QSOMCPTools()
        self.webxr = WebXRAdapter(self.tools)
        self.running = False

    def start_server(self) -> None:
        self.running = True

    def stop_server(self) -> None:
        self.running = False

    def handle_request(self, request: dict) -> dict:
        route = str(request.get("route", ""))
        if route == "qso.read":
            return self.tools.qso_read(str(request["uri"]))
        if route == "qso.patch":
            return self.tools.qso_patch(
                uri=str(request["uri"]),
                delta=dict(request.get("delta", {})),
                actor=str(request.get("actor", "api")),
                policy_version=str(request.get("policy_version", "v1")),
                node_id=str(request.get("node_id", "api")),
            )
        if route == "xr.apply_action":
            return self.webxr.apply_action(
                uri=str(request["uri"]),
                action=dict(request.get("action", {})),
                actor=str(request.get("actor", "webxr-client")),
                policy_version=str(request.get("policy_version", "v1")),
                node_id=str(request.get("node_id", "webxr")),
            )
        if route == "xr.load_qff":
            return self.webxr.load_qff_scene(
                path=str(request["path"]),
                passive=bool(request.get("passive", True)),
            )
        return request
