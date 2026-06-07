from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean
from typing import DefaultDict

from services.transport.models import TransportMode, TransportResponse


@dataclass(slots=True)
class _MetricRow:
    latency_ms: list[float]
    throughput_mbps: list[float]
    error_flags: list[int]


class TransportMetricsCollector:
    def __init__(self) -> None:
        self._rows: DefaultDict[str, _MetricRow] = defaultdict(lambda: _MetricRow([], [], []))

    def record(self, workload_type: str, response: TransportResponse) -> None:
        key = self._key(workload_type, response.mode)
        row = self._rows[key]
        row.latency_ms.append(float(response.elapsed_ms))

        seconds = max(response.elapsed_ms / 1000.0, 0.001)
        mbps = (max(len(response.body), 1) * 8.0) / (seconds * 1_000_000.0)
        row.throughput_mbps.append(mbps)
        row.error_flags.append(0 if response.ok else 1)

    def summary(self) -> dict[str, dict[str, float | int | str]]:
        output: dict[str, dict[str, float | int | str]] = {}
        for key, row in self._rows.items():
            count = len(row.latency_ms)
            if count == 0:
                continue
            output[key] = {
                "samples": count,
                "avg_latency_ms": round(mean(row.latency_ms), 6),
                "avg_throughput_mbps": round(mean(row.throughput_mbps), 6),
                "error_rate": round(sum(row.error_flags) / count, 6),
            }
        return output

    @staticmethod
    def _key(workload_type: str, mode: TransportMode) -> str:
        return f"{workload_type}:{mode.value}"
