from __future__ import annotations

from typing import Any, Dict, List


class QuantumAdvisor:
    def __init__(self, hud, analytics, controls):
        self.hud = hud
        self.analytics = analytics
        self.controls = controls

    def evaluate(self) -> List[Dict[str, Any]]:
        analytics = self.analytics.update()
        if analytics.get("status") != "ok":
            return []

        uri = analytics.get("uri")
        if not uri:
            return []

        recommendations: List[Dict[str, Any]] = []
        if float(analytics.get("tensor_variance", 0.0)) > 1.0:
            recommendations.append({"uri": uri, "patch": {"stabilize": True}, "reason": "high_variance"})
        if int(analytics.get("objects", 0)) == 0:
            recommendations.append({"uri": uri, "patch": {"objects": {"seed": {"visible": True}}}, "reason": "empty_scene"})
        return recommendations

    def render_suggestions(self, recommendations):
        return {"count": len(recommendations), "items": list(recommendations)}
