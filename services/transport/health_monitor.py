from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from statistics import mean
from typing import Deque, DefaultDict

from services.transport.models import TransportMode, TransportResponse


@dataclass(slots=True)
class TransportHealthSnapshot:
    mode: TransportMode
    samples: int
    avg_latency_ms: float
    avg_throughput_mbps: float
    error_rate: float
    health_status: str

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "mode": self.mode.value,
            "samples": self.samples,
            "avg_latency_ms": round(self.avg_latency_ms, 6),
            "avg_throughput_mbps": round(self.avg_throughput_mbps, 6),
            "error_rate": round(self.error_rate, 6),
            "health_status": self.health_status,
        }


class TransportHealthMonitor:
    def __init__(self, window_size: int = 200) -> None:
        self._latency: DefaultDict[TransportMode, Deque[float]] = defaultdict(lambda: deque(maxlen=window_size))
        self._throughput: DefaultDict[TransportMode, Deque[float]] = defaultdict(lambda: deque(maxlen=window_size))
        self._errors: DefaultDict[TransportMode, Deque[int]] = defaultdict(lambda: deque(maxlen=window_size))

    def record(self, response: TransportResponse) -> TransportHealthSnapshot:
        mode = response.mode
        self._latency[mode].append(float(response.elapsed_ms))

        body_bytes = max(len(response.body), 1)
        seconds = max(response.elapsed_ms / 1000.0, 0.001)
        mbps = (body_bytes * 8.0) / (seconds * 1_000_000.0)
        self._throughput[mode].append(mbps)

        is_error = 0 if response.ok else 1
        self._errors[mode].append(is_error)
        return self.snapshot(mode)

    def snapshot(self, mode: TransportMode) -> TransportHealthSnapshot:
        lat = list(self._latency[mode])
        thr = list(self._throughput[mode])
        err = list(self._errors[mode])
        sample_count = len(lat)

        avg_latency = mean(lat) if lat else 0.0
        avg_throughput = mean(thr) if thr else 0.0
        error_rate = float(sum(err) / len(err)) if err else 0.0

        if sample_count == 0:
            health = "unknown"
        elif error_rate >= 0.25:
            health = "degraded"
        elif avg_latency > 400:
            health = "slow"
        else:
            health = "healthy"

        return TransportHealthSnapshot(
            mode=mode,
            samples=sample_count,
            avg_latency_ms=avg_latency,
            avg_throughput_mbps=avg_throughput,
            error_rate=error_rate,
            health_status=health,
        )

    def all_snapshots(self) -> dict[str, dict[str, float | int | str]]:
        out: dict[str, dict[str, float | int | str]] = {}
        for mode in TransportMode:
            out[mode.value] = self.snapshot(mode).to_dict()
        return out
