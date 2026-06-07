from __future__ import annotations

from typing import Any, Dict, List


class PredictiveOptimizer:
    def __init__(self, advisor, controls, analytics, lookahead=3, interval=1.0):
        self.advisor = advisor
        self.controls = controls
        self.analytics = analytics
        self.lookahead = lookahead
        self.interval = interval
        self.enabled = True

    def run_loop(self) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        recommendations = self.advisor.evaluate()
        actions: List[Dict[str, Any]] = []
        for recommendation in recommendations[: self.lookahead]:
            uri = recommendation.get("uri")
            patch = recommendation.get("patch")
            if not uri or not isinstance(patch, dict):
                continue
            self.controls.patch_selected(patch) if getattr(self.controls, "selected_qso", None) == uri else None
            actions.append({"uri": uri, "patch": patch, "reason": recommendation.get("reason", "predictive")})
        return actions
