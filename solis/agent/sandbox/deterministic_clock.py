from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class DeterministicClock:
    start: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)
    step_seconds: int = 1
    tick_count: int = 0

    def now(self) -> datetime:
        return self.start + timedelta(seconds=self.tick_count * self.step_seconds)

    def tick(self) -> datetime:
        self.tick_count += 1
        return self.now()
