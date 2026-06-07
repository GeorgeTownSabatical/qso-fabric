from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from solis.schemas import SCHEMA_VERSION
from solis.shared.canonical_json import canonical_json
from solis.shared.hashing import sha256_hex_obj
from storage.event_store import EventStore

Reducer = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


class SnapshotStoreLike(Protocol):
    def put(self, uri: str, blob: bytes, label: str | None = None) -> str: ...


@dataclass(frozen=True)
class ReplaySnapshot:
    schema_version: str
    uri: str
    event_count: int
    event_chain_hash: str
    state_hash: str
    state: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "uri": self.uri,
            "event_count": self.event_count,
            "event_chain_hash": self.event_chain_hash,
            "state_hash": self.state_hash,
            "state": dict(self.state),
        }


def build_snapshot_document(*, uri: str, state: Mapping[str, Any], events: list[dict[str, Any]]) -> ReplaySnapshot:
    state_dict = {str(key): value for key, value in dict(state).items()}
    return ReplaySnapshot(
        schema_version=SCHEMA_VERSION,
        uri=uri,
        event_count=len(events),
        event_chain_hash=sha256_hex_obj(events),
        state_hash=sha256_hex_obj(state_dict),
        state=state_dict,
    )


class DeterministicReplayAPI:
    def __init__(self, *, event_store: EventStore, snapshot_store: SnapshotStoreLike) -> None:
        self.event_store = event_store
        self.snapshot_store = snapshot_store

    def append(self, event: Mapping[str, Any]) -> None:
        self.event_store.append(dict(event))

    def verify_append_only_chain(self) -> bool:
        return bool(self.event_store.verify_chain())

    def snapshot(self, *, uri: str, state: Mapping[str, Any], label: str | None = None) -> dict[str, Any]:
        events = self.event_store.query(uri=uri)
        snapshot = build_snapshot_document(uri=uri, state=state, events=events)
        blob = canonical_json(snapshot.as_dict()).encode("utf-8")
        tag = self.snapshot_store.put(uri, blob, label=label)
        return {"tag": tag, "snapshot": snapshot.as_dict()}

    def replay(
        self,
        *,
        uri: str,
        initial_state: Mapping[str, Any],
        reducer: Reducer,
    ) -> dict[str, Any]:
        state = {str(key): value for key, value in dict(initial_state).items()}
        events = self.event_store.query(uri=uri)
        for event in events:
            delta = event.get("delta", {})
            if isinstance(delta, dict):
                state = reducer(state, dict(delta))
        return {
            "state": state,
            "state_hash": sha256_hex_obj(state),
            "event_chain_hash": sha256_hex_obj(events),
            "event_count": len(events),
        }
