from __future__ import annotations

from typing import Dict


class DistributedOptimizerService:
    def recommend(self, rewards: Dict[str, float]) -> Dict[str, str | float]:
        if not rewards:
            return {"best_node": "none", "tuning_parameter": 1.0, "hint": "no-data"}

        best_node = max(rewards, key=rewards.get)
        best_reward = rewards[best_node]
        return {
            "best_node": best_node,
            "best_reward": round(best_reward, 4),
            "tuning_parameter": max(0.1, min(2.0, 1.0 + best_reward / 10.0)),
            "hint": "broadcast_policy_from_best_node",
        }
