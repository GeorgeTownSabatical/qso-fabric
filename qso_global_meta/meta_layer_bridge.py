from __future__ import annotations

import json


class GDMLBridge:
    def __init__(self, local_meta_layer, node_registry, meta_sync, reward_aggregator):
        self.local_meta = local_meta_layer
        self.node_registry = node_registry
        self.meta_sync = meta_sync
        self.reward_aggregator = reward_aggregator

    def report_local_performance(self):
        local_metrics = self.local_meta.suggest() if hasattr(self.local_meta, "suggest") else {}
        node_id = str(local_metrics.get("node_id", "local"))
        reward = float(local_metrics.get("reward_signal", 0.0))
        uri = str(local_metrics.get("uri", "qso://meta.local"))
        self.reward_aggregator.submit_reward(node_id, uri, reward)
        return {"node_id": node_id, "uri": uri, "reward": reward}

    def synchronize_global_meta(self):
        active = self.node_registry.get_active_nodes()
        updates = {node_id: {"version": "v1", "mode": "balanced"} for node_id in active}
        if hasattr(self.meta_sync, "ingest_policy") and hasattr(self.meta_sync, "sync"):
            for node_id, policy in updates.items():
                self.meta_sync.ingest_policy(node_id=node_id, policy=policy)
            decision = self.meta_sync.sync(total_nodes=len(active) if active else None)
            return {"nodes": active, "sync": decision}

        merged = self.meta_sync.merge_policy_updates(
            {
                node_id: {
                    **policy,
                    "signature": self.meta_sync.crypto.sign(
                        json.dumps({"node_id": node_id, "update": policy}, sort_keys=True)
                    ),
                }
                for node_id, policy in updates.items()
            }
        )
        return {"nodes": active, "policies": merged}
