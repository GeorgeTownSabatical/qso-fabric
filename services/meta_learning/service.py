from __future__ import annotations

from collections import deque
from statistics import mean
from typing import Deque, Dict

from api.schemas.models import MetaMetrics
from services.meta_learning.transport_optimizer import TransportOptimizer


class MetaLearningService:
    def __init__(self, max_window: int = 500) -> None:
        self._samples: Deque[MetaMetrics] = deque(maxlen=max_window)
        self._transport_optimizer = TransportOptimizer()

    def observe(self, metrics: MetaMetrics) -> None:
        self._samples.append(metrics)

    def suggest(self) -> Dict[str, float | str]:
        if not self._samples:
            return {"policy_update": "none", "scaling_hint": "stable"}

        avg_latency = mean(s.latency_ms for s in self._samples)
        avg_throughput = mean(s.throughput for s in self._samples)
        avg_error = mean(s.error_rate for s in self._samples)

        scaling_hint = "scale_out" if avg_latency > 120 and avg_throughput > 100 else "stable"
        policy_update = "tighten_validation" if avg_error > 0.02 else "keep"

        return {
            "avg_latency_ms": round(avg_latency, 3),
            "avg_throughput": round(avg_throughput, 3),
            "avg_error_rate": round(avg_error, 5),
            "policy_update": policy_update,
            "scaling_hint": scaling_hint,
        }

    def suggest_transport(
        self,
        *,
        workload: str,
        latency_ms: float,
        error_rate: float,
        volatility: float = 0.0,
    ) -> Dict[str, float | str]:
        return self._transport_optimizer.recommend(
            {
                "workload": workload,
                "latency_ms": latency_ms,
                "error_rate": error_rate,
                "volatility": volatility,
            }
        )
