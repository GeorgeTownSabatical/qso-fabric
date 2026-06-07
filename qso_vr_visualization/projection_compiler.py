from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


def _is_vec3(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 3 and all(isinstance(v, (int, float)) for v in value)


class ProjectionCompiler:
    def compile(self, payload: Dict[str, Any], fallback_uri: str | None = None) -> Dict[str, Any] | None:
        uri = str(payload.get("uri") or fallback_uri or "")
        if not uri:
            return None

        delta = payload.get("delta", {})
        if not isinstance(delta, dict):
            return None

        render_delta = self._build_render_delta(delta)
        projection: Dict[str, Any] = {
            "uri": uri,
            "event_index": payload.get("event_index"),
            "source": payload.get("source", "live"),
            "render_delta": render_delta,
            "meta": {},
        }
        for token_key in ("cursor_token", "uri_cursor_token"):
            if token_key in payload:
                projection[token_key] = payload[token_key]

        event = payload.get("event")
        if isinstance(event, dict):
            projection["meta"]["timestamp"] = event.get("timestamp")
            projection["meta"]["actor"] = event.get("actor")
            projection["meta"]["policy_version"] = event.get("policy_version")

        for key in ("entangled_from", "relationship", "strength", "sync_mode", "latency_target_ms"):
            if key in payload:
                projection["meta"][key] = payload[key]

        return projection

    def _build_render_delta(self, delta: Dict[str, Any]) -> Dict[str, Any]:
        object_ops: List[Dict[str, Any]] = []
        if isinstance(delta.get("objects"), dict):
            for object_id in sorted(delta["objects"]):
                object_ops.append({"id": object_id, "patch": deepcopy(delta["objects"][object_id])})

        global_patch = {k: deepcopy(v) for k, v in delta.items() if k != "objects"}
        out: Dict[str, Any] = {"objects": object_ops, "global": global_patch}

        position = self._extract_position(delta)
        if position is not None:
            out["spatial"] = {"position": position}
        return out

    def _extract_position(self, delta: Dict[str, Any]) -> list[float] | None:
        direct = delta.get("position")
        if _is_vec3(direct):
            return [float(v) for v in direct]

        transform = delta.get("transform")
        if isinstance(transform, dict) and _is_vec3(transform.get("position")):
            return [float(v) for v in transform["position"]]

        objects = delta.get("objects")
        if isinstance(objects, dict):
            for object_id in sorted(objects):
                patch = objects.get(object_id)
                if isinstance(patch, dict) and _is_vec3(patch.get("position")):
                    return [float(v) for v in patch["position"]]

        return None
