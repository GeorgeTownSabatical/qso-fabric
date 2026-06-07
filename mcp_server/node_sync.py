from __future__ import annotations

from typing import Any, Dict, List

from federation.checkpointing.hash_chain import checkpoint_hash
from federation.replication import ReplicationService

class NodeSync:
    def __init__(self) -> None:
        self.replication = ReplicationService()
        self._remote_events: Dict[str, List[Dict[str, Any]]] = {}

    def replicate_event(self, event: Dict[str, Any], target_node: str = "remote") -> Dict[str, Any]:
        local_events = self._remote_events.setdefault(target_node, [])
        batch = self.replication.build_batch(
            source_node="local",
            target_node=target_node,
            events=[event],
            checkpoint_hash=checkpoint_hash(local_events + [event]),
        )
        merged = self.replication.apply_batch(local_events, batch)
        self._remote_events[target_node] = merged
        return {
            "target_node": target_node,
            "replicated_events": len(batch.events),
            "total_events": len(merged),
            "checkpoint_hash": batch.checkpoint_hash,
        }

    def sync_entanglements(self) -> Dict[str, Any]:
        return {"status": "ok", "replicated_nodes": sorted(self._remote_events)}
