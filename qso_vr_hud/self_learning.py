from __future__ import annotations

from typing import Any, Dict


class SelfLearningLayer:
    def __init__(self, policy_engine, predictive_optimizer, analytics, learning_rate=0.1, interval=5.0):
        self.policy_engine = policy_engine
        self.predictive_optimizer = predictive_optimizer
        self.analytics = analytics
        self.learning_rate = learning_rate
        self.interval = interval
        self.enabled = True
        self.qso_rewards = {}

    def run_loop(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled"}

        analytics = self.analytics.update()
        if analytics.get("status") != "ok":
            return {"status": "idle", "reason": analytics.get("reason", "analytics_unavailable")}

        uri = analytics.get("uri")
        if uri:
            reward = max(0.0, 1.0 - float(analytics.get("tensor_variance", 0.0)))
            prior = float(self.qso_rewards.get(uri, 0.0))
            updated = prior + self.learning_rate * (reward - prior)
            self.qso_rewards[uri] = round(updated, 6)

        return {"status": "ok", "rewards": dict(self.qso_rewards)}
