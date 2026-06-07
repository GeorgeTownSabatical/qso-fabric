from __future__ import annotations


def canonical_merge(events_a: list[dict], events_b: list[dict]) -> list[dict]:
    merged = events_a + events_b
    return sorted(merged, key=lambda e: (str(e.get("timestamp", "")), str(e.get("event_id", ""))))
