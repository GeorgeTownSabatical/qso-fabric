from __future__ import annotations

from typing import Any, Dict


class AnalyticsOverlay:
    def __init__(self, hud, controller) -> None:
        self.hud = hud
        self.controller = controller

    def update(self) -> Dict[str, Any]:
        uri = getattr(self.hud, "selected_qso", None)
        if not uri:
            return {"status": "idle", "reason": "no_selected_qso"}

        state = self.controller.read(uri).get("state_layer", {})
        tensor = state.get("tensor")
        return {
            "status": "ok",
            "uri": uri,
            "tensor_variance": self._tensor_variance(tensor),
            "tensor_correlation": self._tensor_correlation(uri),
            "objects": len(state.get("objects", {})) if isinstance(state.get("objects"), dict) else 0,
        }

    def _tensor_variance(self, tensor):
        if tensor is None:
            return 0.0
        if isinstance(tensor, list) and tensor and all(isinstance(v, (int, float)) for v in tensor):
            mean = sum(tensor) / len(tensor)
            return sum((v - mean) ** 2 for v in tensor) / len(tensor)
        return 1.0

    def _tensor_correlation(self, uri):
        _ = uri
        return 0.5
