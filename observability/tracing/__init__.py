from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Dict, Iterator, List


@dataclass
class Span:
    name: str
    started_at: str
    ended_at: str
    duration_ms: float
    attrs: Dict[str, str]


class TraceCollector:
    def __init__(self) -> None:
        self._spans: List[Span] = []

    @contextmanager
    def span(self, name: str, **attrs: str) -> Iterator[None]:
        started_wall = datetime.now(timezone.utc).isoformat()
        t0 = perf_counter()
        try:
            yield
        finally:
            duration_ms = (perf_counter() - t0) * 1000.0
            self._spans.append(
                Span(
                    name=name,
                    started_at=started_wall,
                    ended_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=round(duration_ms, 6),
                    attrs={str(k): str(v) for k, v in attrs.items()},
                )
            )

    def export(self) -> List[Dict[str, str | float]]:
        return [
            {
                "name": span.name,
                "started_at": span.started_at,
                "ended_at": span.ended_at,
                "duration_ms": span.duration_ms,
                "attrs": span.attrs,
            }
            for span in self._spans
        ]
