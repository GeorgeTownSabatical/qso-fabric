from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Set


class EventIndex:
    """Secondary indexes for event queries by actor/uri/policy_version."""

    def __init__(self) -> None:
        self._by_actor: Dict[str, Set[str]] = defaultdict(set)
        self._by_uri: Dict[str, List[str]] = defaultdict(list)
        self._by_policy: Dict[str, Set[str]] = defaultdict(set)
        self._ts_by_id: Dict[str, datetime] = {}

    def add(self, event: Any) -> None:
        if hasattr(event, "model_dump"):
            row = event.model_dump(mode="json")
        elif isinstance(event, dict):
            row = dict(event)
        else:
            raise TypeError(f"unsupported event type: {type(event)!r}")

        event_id = str(row["event_id"])
        actor = str(row.get("actor", ""))
        uri = str(row.get("object_uri", ""))
        policy = str(row.get("policy_version", ""))
        timestamp_raw = str(row.get("timestamp", ""))

        if actor:
            self._by_actor[actor].add(event_id)
        if uri:
            self._by_uri[uri].append(event_id)
        if policy:
            self._by_policy[policy].add(event_id)

        if timestamp_raw:
            try:
                self._ts_by_id[event_id] = datetime.fromisoformat(timestamp_raw)
            except ValueError:
                pass

    def by_actor(self, actor: str) -> Set[str]:
        return set(self._by_actor.get(actor, set()))

    def by_uri(self, uri: str) -> List[str]:
        return list(self._by_uri.get(uri, []))

    def by_policy(self, policy_version: str) -> Set[str]:
        return set(self._by_policy.get(policy_version, set()))

    def since(self, timestamp: datetime) -> Set[str]:
        return {event_id for event_id, ts in self._ts_by_id.items() if ts >= timestamp}
