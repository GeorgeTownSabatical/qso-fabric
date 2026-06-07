from __future__ import annotations

from collections import defaultdict
from typing import Dict, List


class RewardAggregationService:
    def __init__(self) -> None:
        self._rewards: Dict[str, List[float]] = defaultdict(list)

    def ingest(self, node_id: str, reward: float) -> None:
        self._rewards[node_id].append(reward)

    def aggregate(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for node_id, rewards in self._rewards.items():
            out[node_id] = sum(rewards) / len(rewards) if rewards else 0.0
        return out
