from __future__ import annotations

from typing import Mapping


class TransportOptimizer:
    """Risk-aware mode recommender for workload routing."""

    def recommend(self, metrics: Mapping[str, float | str]) -> dict[str, float | str]:
        workload = str(metrics.get("workload", "research"))
        error_rate = float(metrics.get("error_rate", 0.0))
        latency_ms = float(metrics.get("latency_ms", 0.0))
        volatility = float(metrics.get("volatility", 0.0))

        if workload == "market_execution":
            mode = "direct" if latency_ms <= 250 and error_rate < 0.1 else "vpn"
        elif workload == "model_training":
            mode = "vpn" if error_rate > 0.05 else "direct"
        else:
            if error_rate > 0.2:
                mode = "vpn"
            elif volatility < 0.35 and latency_ms < 500:
                mode = "tor"
            else:
                mode = "direct"

        confidence = max(0.1, min(0.99, 1.0 - error_rate - min(volatility, 0.5) * 0.3))
        return {
            "recommended_mode": mode,
            "confidence_score": round(confidence, 4),
            "projected_latency_ms": round(latency_ms * (1.05 if mode == "vpn" else 1.2 if mode == "tor" else 1.0), 6),
            "risk_adjusted_score": round((1.0 - error_rate) * confidence, 6),
        }
