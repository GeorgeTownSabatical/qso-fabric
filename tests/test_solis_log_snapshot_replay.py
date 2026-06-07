from __future__ import annotations

from pathlib import Path

from solis.shared.log_snapshot_replay import DeterministicReplayAPI
from storage.event_store import InMemoryEventStore, JsonlEventStore
from storage.snapshot_store import InMemorySnapshotStore


def _sum_reducer(state: dict[str, object], delta: dict[str, object]) -> dict[str, object]:
    out = dict(state)
    for key, value in delta.items():
        key_name = str(key)
        current = out.get(key_name)
        if isinstance(value, (int, float)) and isinstance(current, (int, float)):
            out[key_name] = float(current) + float(value)
        elif isinstance(value, (int, float)):
            out[key_name] = float(value)
        else:
            out[key_name] = value
    return out


def test_deterministic_replay_api_with_inmemory_append_only_chain() -> None:
    store = InMemoryEventStore()
    snapshots = InMemorySnapshotStore()
    replay_api = DeterministicReplayAPI(event_store=store, snapshot_store=snapshots)

    replay_api.append(
        {
            "event_id": "evt-1",
            "timestamp": "2026-02-25T00:00:00+00:00",
            "actor": "tester",
            "object_uri": "qso://solis.star.demo",
            "delta": {"mass": 1.0},
            "signature": "sig-1",
            "policy_version": "v1",
            "node_id": "node-a",
        }
    )
    replay_api.append(
        {
            "event_id": "evt-2",
            "timestamp": "2026-02-25T00:00:01+00:00",
            "actor": "tester",
            "object_uri": "qso://solis.star.demo",
            "delta": {"mass": 0.5, "entropy_index": 0.2},
            "signature": "sig-2",
            "policy_version": "v1",
            "node_id": "node-a",
        }
    )

    assert replay_api.verify_append_only_chain() is True
    replayed = replay_api.replay(
        uri="qso://solis.star.demo",
        initial_state={"mass": 0.0},
        reducer=_sum_reducer,
    )
    assert replayed["event_count"] == 2
    assert replayed["state"]["mass"] == 1.5
    assert replayed["state"]["entropy_index"] == 0.2

    snap = replay_api.snapshot(uri="qso://solis.star.demo", state=replayed["state"], label="t0")
    assert snap["tag"] == "t0"
    assert "t0" in snapshots.list("qso://solis.star.demo")


def test_append_only_chain_detects_tampering() -> None:
    store = InMemoryEventStore()
    store.append(
        {
            "event_id": "evt-x",
            "timestamp": "2026-02-25T00:00:00+00:00",
            "actor": "tester",
            "object_uri": "qso://tamper",
            "delta": {"v": 1},
            "signature": "sig",
            "policy_version": "v1",
            "node_id": "node-a",
        }
    )
    assert store.verify_chain() is True
    store._rows[0]["delta"]["v"] = 99  # type: ignore[index]
    assert store.verify_chain() is False


def test_jsonl_event_store_chain_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    store = JsonlEventStore(path)
    store.append(
        {
            "event_id": "evt-a",
            "timestamp": "2026-02-25T00:00:00+00:00",
            "actor": "tester",
            "object_uri": "qso://jsonl",
            "delta": {"n": 1},
            "signature": "sig-a",
            "policy_version": "v1",
            "node_id": "node-a",
        }
    )
    store.append(
        {
            "event_id": "evt-b",
            "timestamp": "2026-02-25T00:00:01+00:00",
            "actor": "tester",
            "object_uri": "qso://jsonl",
            "delta": {"n": 2},
            "signature": "sig-b",
            "policy_version": "v1",
            "node_id": "node-a",
        }
    )
    assert store.verify_chain() is True

    reopened = JsonlEventStore(path)
    assert reopened.verify_chain() is True
