from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from federation.reconciliation.merge import canonical_merge


@dataclass(frozen=True)
class ReplicationBatch:
    source_node: str
    target_node: str
    events: List[Dict[str, Any]]
    checkpoint_hash: str


class ReplicationService:
    """Deterministic replication helper for append-only event logs."""

    def build_batch(
        self,
        *,
        source_node: str,
        target_node: str,
        events: List[Dict[str, Any]],
        checkpoint_hash: str,
    ) -> ReplicationBatch:
        return ReplicationBatch(
            source_node=source_node,
            target_node=target_node,
            events=[dict(event) for event in events],
            checkpoint_hash=checkpoint_hash,
        )

    def apply_batch(
        self,
        local_events: List[Dict[str, Any]],
        batch: ReplicationBatch,
    ) -> List[Dict[str, Any]]:
        return canonical_merge(local_events, batch.events)
