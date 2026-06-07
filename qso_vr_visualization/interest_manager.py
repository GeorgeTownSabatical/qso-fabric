from __future__ import annotations

from typing import Any, Dict


def _coerce_vec3(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    if not all(isinstance(v, (int, float)) for v in value):
        return None
    return float(value[0]), float(value[1]), float(value[2])


class InterestManager:
    def __init__(self, default_radius: float = 150.0) -> None:
        self.default_radius = float(default_radius)

    def is_relevant(self, uri: str, projection: Dict[str, Any], viewpoint: Dict[str, Any] | None = None) -> bool:
        if viewpoint is None:
            return True

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

        center = _coerce_vec3(viewpoint.get("center"))
        if center is None:
            return True

        radius = viewpoint.get("radius", self.default_radius)
        if not isinstance(radius, (int, float)) or radius <= 0:
            radius = self.default_radius

        position = self._projection_position(projection)
        if position is None:
            return True

        dx = position[0] - center[0]
        dy = position[1] - center[1]
        dz = position[2] - center[2]
        return dx * dx + dy * dy + dz * dz <= float(radius) * float(radius)

    @staticmethod
    def _projection_position(projection: Dict[str, Any]) -> tuple[float, float, float] | None:
        render_delta = projection.get("render_delta")
        if not isinstance(render_delta, dict):
            return None
        spatial = render_delta.get("spatial")
        if not isinstance(spatial, dict):
            return None
        return _coerce_vec3(spatial.get("position"))
