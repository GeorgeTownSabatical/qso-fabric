from __future__ import annotations

from typing import Any, Mapping


class ProviderScoringEngine:
    def score(self, telemetry: Mapping[str, Any]) -> dict[str, float | str]:
        uptime = float(telemetry.get("uptime", 0.0))
        error_rate = float(telemetry.get("error_rate", 1.0))
        latency_ms = float(telemetry.get("latency_ms", 1_000.0))

        reliability = max(0.0, min(1.0, uptime * (1.0 - error_rate)))
        latency_factor = max(0.0, min(1.0, 1.0 - min(latency_ms, 2_000.0) / 2_000.0))
        score = round(0.7 * reliability + 0.3 * latency_factor, 6)
        tier = "gold" if score >= 0.85 else "silver" if score >= 0.6 else "bronze"
        return {
            "score": score,
            "tier": tier,
            "reliability": round(reliability, 6),
            "latency_factor": round(latency_factor, 6),
        }
