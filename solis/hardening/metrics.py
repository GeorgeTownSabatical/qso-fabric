from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict


class PrometheusMetricRegistry:
    def __init__(self) -> None:
        self.counters: DefaultDict[str, float] = defaultdict(float)
        self.gauges: DefaultDict[str, float] = defaultdict(float)

    def inc(self, name: str, value: float = 1.0) -> None:
        self.counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        self.gauges[name] = value

    def render(self) -> str:
        lines: list[str] = []
        for key, value in sorted(self.counters.items()):
            lines.append(f"{key} {value}")
        for key, value in sorted(self.gauges.items()):
            lines.append(f"{key} {value}")
        return "\n".join(lines) + "\n"
