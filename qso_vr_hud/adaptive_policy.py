from __future__ import annotations

from typing import Any, Dict


class AdaptivePolicyLayer:
    def __init__(self, policy_engine, analytics, adaptation_rate=0.05, interval=2.0):
        self.policy_engine = policy_engine
        self.analytics = analytics
        self.adaptation_rate = adaptation_rate
        self.interval = interval
        self.enabled = True

    def run_loop(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled"}

        analytics = self.analytics.update()
        if analytics.get("status") != "ok":
            return {"status": "idle", "reason": analytics.get("reason", "analytics_unavailable")}

        latency_score = float(analytics.get("tensor_variance", 0.0))
        if latency_score > 1.0:
            proposed_mode = "stability"
        else:
            proposed_mode = "balanced"

        return self.policy_engine.apply_policy_hint(
            {
                "mode": proposed_mode,
                "adaptation_rate": self.adaptation_rate,
                "source": "adaptive_policy_layer",
            }
        )
