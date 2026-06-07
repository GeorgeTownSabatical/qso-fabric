from __future__ import annotations

from datetime import datetime, timedelta, timezone


class LogicalClock:
    def __init__(self) -> None:
        self._tick = 0
        self._epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def next_datetime(self) -> datetime:
        self._tick += 1
        return self._epoch + timedelta(microseconds=self._tick)

    @property
    def tick(self) -> int:
        return self._tick
