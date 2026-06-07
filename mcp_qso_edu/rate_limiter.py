from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(slots=True)
class RateLimitConfig:
    max_events_per_minute: int = 120
    max_objects: int = 200
    max_entanglements: int = 400


class SlidingWindowRateLimiter:
    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self._events: deque[datetime] = deque()
        self._objects = 0
        self._entanglements = 0

    def record_event(self) -> None:
        now = datetime.now(timezone.utc)
        self._evict_old(now)
        if len(self._events) >= self.config.max_events_per_minute:
            raise RuntimeError("sandbox rate limit exceeded: max_events_per_minute")
        self._events.append(now)

    def record_object(self) -> None:
        self.record_event()
        self._objects += 1
        if self._objects > self.config.max_objects:
            raise RuntimeError("sandbox object cap exceeded")

    def record_entanglement(self) -> None:
        self.record_event()
        self._entanglements += 1
        if self._entanglements > self.config.max_entanglements:
            raise RuntimeError("sandbox entanglement cap exceeded")

    def snapshot(self) -> dict[str, int]:
        return {
            "events_last_minute": len(self._events),
            "objects": self._objects,
            "entanglements": self._entanglements,
        }

    def _evict_old(self, now: datetime) -> None:
        cutoff = now - timedelta(minutes=1)
        while self._events and self._events[0] < cutoff:
            self._events.popleft()
