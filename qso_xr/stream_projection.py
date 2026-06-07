from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple


def _is_vec3(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 3 and all(isinstance(v, (int, float)) for v in value)


class XRStreamProjection:
    """Deterministic projection queue with explicit backpressure handling."""

    def __init__(self, *, max_size: int = 256, backpressure: str = "block") -> None:
        self.max_size = max(1, int(max_size))
        self.backpressure = str(backpressure)
        self._queue: List[Dict[str, Any]] = []

    def publish(self, payload: Dict[str, Any]) -> bool:
        row = deepcopy(payload)
        if len(self._queue) >= self.max_size:
            if self.backpressure == "drop_oldest":
                self._queue.pop(0)
            elif self.backpressure == "drop_newest":
                return False
            else:
                raise BufferError("stream queue is full")
        self._queue.append(row)
        return True

    def drain(self, *, limit: int | None = None) -> List[Dict[str, Any]]:
        if limit is None:
            limit = len(self._queue)
        take = max(0, min(int(limit), len(self._queue)))
        out = self._queue[:take]
        self._queue = self._queue[take:]
        return out

    def size(self) -> int:
        return len(self._queue)

    @staticmethod
    def compile_delta(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        return _diff_dict(dict(before), dict(after))

    @staticmethod
    def is_relevant(projection: Dict[str, Any], viewpoint: Dict[str, Any] | None = None) -> bool:
        if viewpoint is None:
            return True

        uri = str(projection.get("uri", ""))

        focus_uris = viewpoint.get("focus_uris")
        if isinstance(focus_uris, list) and focus_uris and uri not in focus_uris:
            return False

        allow_prefixes = viewpoint.get("allow_prefixes")
        if isinstance(allow_prefixes, list) and allow_prefixes:
            if not any(uri.startswith(str(prefix)) for prefix in allow_prefixes):
                return False

        deny_prefixes = viewpoint.get("deny_prefixes")
        if isinstance(deny_prefixes, list) and deny_prefixes:
            if any(uri.startswith(str(prefix)) for prefix in deny_prefixes):
                return False

        center = viewpoint.get("center")
        if not _is_vec3(center):
            return True
        radius = viewpoint.get("radius", 150.0)
        if not isinstance(radius, (int, float)) or radius <= 0:
            radius = 150.0

        position = _extract_projection_position(projection)
        if position is None:
            return True

        dx = position[0] - float(center[0])
        dy = position[1] - float(center[1])
        dz = position[2] - float(center[2])
        return dx * dx + dy * dy + dz * dz <= float(radius) * float(radius)


def _extract_projection_position(projection: Dict[str, Any]) -> Tuple[float, float, float] | None:
    render_delta = projection.get("render_delta")
    if not isinstance(render_delta, dict):
        return None
    spatial = render_delta.get("spatial")
    if not isinstance(spatial, dict):
        return None
    pos = spatial.get("position")
    if not _is_vec3(pos):
        return None
    return float(pos[0]), float(pos[1]), float(pos[2])


def _diff_dict(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    keys = sorted(set(before.keys()) | set(after.keys()))
    out: Dict[str, Any] = {}
    deleted: List[str] = []
    for key in keys:
        in_before = key in before
        in_after = key in after
        if in_before and not in_after:
            deleted.append(key)
            continue
        if not in_before and in_after:
            out[key] = deepcopy(after[key])
            continue
        left = before[key]
        right = after[key]
        if isinstance(left, dict) and isinstance(right, dict):
            nested = _diff_dict(dict(left), dict(right))
            if nested:
                out[key] = nested
            continue
        if left != right:
            out[key] = deepcopy(right)
    if deleted:
        out["__deleted__"] = deleted
    return out
