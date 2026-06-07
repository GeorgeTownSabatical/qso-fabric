from __future__ import annotations

from typing import Any

from services.event_log.service import EventLogService


class QuantumReplayEngine:
    def __init__(self, event_log: EventLogService) -> None:
        self.event_log = event_log

    def replay(self, uri: str, *, strict: bool = True) -> dict[str, Any]:
        state: dict[str, Any] = {}
        events = self.event_log.replay(uri, strict=strict)
        for event in events:
            for key, value in event.delta.items():
                state[key] = value
        return {
            "uri": uri,
            "events": [event.model_dump(mode="json") for event in events],
            "state": state,
        }
