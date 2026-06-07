from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class Event:
    event_id: str
    actor: str
    object_uri: str
    delta: Dict[str, Any]
    signature: str
    policy_version: str
    timestamp: str = datetime.now(timezone.utc).isoformat()


class EventLogEngine:
    def __init__(self) -> None:
        self.events: List[Event] = []

    def append_event(self, event: Event) -> None:
        self.events.append(event)

    def query_events(self, uri: str) -> List[Event]:
        return [e for e in self.events if e.object_uri == uri]

    def replay(self, uri: str) -> List[Event]:
        return self.query_events(uri)
