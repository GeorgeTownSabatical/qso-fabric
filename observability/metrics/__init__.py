from __future__ import annotations

from collections import defaultdict
from statistics import mean
from threading import RLock
from typing import Dict, List


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = RLock()

    def inc(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += float(value)

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = float(value)

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._histograms[name].append(float(value))

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            hist = {
                name: {
                    "count": float(len(values)),
                    "avg": float(mean(values)) if values else 0.0,
                    "min": float(min(values)) if values else 0.0,
                    "max": float(max(values)) if values else 0.0,
                }
                for name, values in self._histograms.items()
            }
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": hist,
            }
