from __future__ import annotations

from datetime import datetime, timezone

from federation.replication import ReplicationService
from federation.sharding import shard_for_uri, shard_uris
from mcp_server.node_sync import NodeSync
from storage.checkpoint_store import InMemoryCheckpointStore
from storage.event_store import InMemoryEventStore
from storage.snapshot_store import InMemorySnapshotStore


def test_inmemory_event_store_query() -> None:
    store = InMemoryEventStore()
    event = {
        "event_id": "e1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": "tester",
        "object_uri": "qso://a",
        "delta": {"v": 1},
        "signature": "sig",
        "policy_version": "v1",
        "node_id": "local",
    }
    store.append(event)

    rows = store.query(uri="qso://a")
    assert len(rows) == 1
    assert rows[0]["actor"] == "tester"


def test_checkpoint_and_snapshot_store() -> None:
    checkpoints = InMemoryCheckpointStore()
    snapshots = InMemorySnapshotStore()

    row = checkpoints.put("qso://a", 1, "hash-1")
    assert row["event_count"] == 1
    assert checkpoints.latest("qso://a")["hash_chain"] == "hash-1"

    tag = snapshots.put("qso://a", b"blob")
    assert tag in snapshots.list("qso://a")
    assert snapshots.get("qso://a", tag) == b"blob"


def test_replication_service_and_sharding() -> None:
    replication = ReplicationService()
    local = [{"event_id": "a", "timestamp": "2026-01-01T00:00:00+00:00"}]
    remote_batch = replication.build_batch(
        source_node="n1",
        target_node="n2",
        events=[{"event_id": "b", "timestamp": "2026-01-01T00:00:01+00:00"}],
        checkpoint_hash="h",
    )
    merged = replication.apply_batch(local, remote_batch)
    assert [row["event_id"] for row in merged] == ["a", "b"]

    shard_idx = shard_for_uri("qso://a", shard_count=4)
    assert 0 <= shard_idx < 4
    mapping = shard_uris(["qso://a", "qso://b"], shard_count=2)
    assert sum(len(v) for v in mapping.values()) == 2


def test_node_sync_replication_smoke() -> None:
    sync = NodeSync()
    out = sync.replicate_event(
        {
            "event_id": "e1",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "object_uri": "qso://a",
            "delta": {"v": 1},
        },
        target_node="node-b",
    )
    assert out["target_node"] == "node-b"
    assert out["replicated_events"] == 1
