from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TimelineEvent:
    event_id: str
    timestamp: float
    actor: str
    delta: dict
    signature: str
