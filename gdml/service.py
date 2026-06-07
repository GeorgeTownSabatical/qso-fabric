from __future__ import annotations

from typing import Any, Dict

from gdml.distributed_optimizer.service import DistributedOptimizerService
from gdml.global_registry.service import GlobalRegistryService
from gdml.policy_sync.service import PolicySyncService
from gdml.reward_aggregation.service import RewardAggregationService
from services.crypto_access.service import CryptoAccessService
from services.event_log.clock import LogicalClock
from services.event_log.service import EventLogService


class GDMLCoordinator:
    def __init__(self, event_log: EventLogService, crypto: CryptoAccessService, clock: LogicalClock | None = None) -> None:
        self.registry = GlobalRegistryService()
        self.rewards = RewardAggregationService()
        self.policy_sync = PolicySyncService(event_log, crypto, clock)
        self.optimizer = DistributedOptimizerService()

    def ingest_reward(self, node_id: str, reward: float) -> None:
        self.rewards.ingest(node_id, reward)

    def global_optimize(self) -> Dict[str, Any]:
        summary = self.rewards.aggregate()
        recommendation = self.optimizer.recommend(summary)
        self.policy_sync.publish(
            {
                "version": "v2",
                "mode": "reward-optimized",
                "leader": str(recommendation["best_node"]),
            },
            actor="gdml-optimizer",
            node_id="gdml-core",
        )
        return recommendation
