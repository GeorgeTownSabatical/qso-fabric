from __future__ import annotations


def canonical_event_key(event: dict) -> tuple[str, str]:
    return str(event.get("timestamp", "")), str(event.get("event_id", ""))
