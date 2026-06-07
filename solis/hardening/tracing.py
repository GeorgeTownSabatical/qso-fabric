from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class SpanRecord:
    name: str
    started_at: float
    ended_at: float

    @property
    def duration_ms(self) -> float:
        return (self.ended_at - self.started_at) * 1000.0


class Tracer:
    def __init__(self) -> None:
        self.spans: list[SpanRecord] = []

    @contextlib.contextmanager
    def span(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            end = time.perf_counter()
            self.spans.append(SpanRecord(name=name, started_at=start, ended_at=end))
