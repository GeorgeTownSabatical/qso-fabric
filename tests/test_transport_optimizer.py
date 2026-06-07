from __future__ import annotations

from services.meta_learning.transport_optimizer import TransportOptimizer


def test_transport_optimizer_prefers_direct_or_vpn_for_market_execution() -> None:
    optimizer = TransportOptimizer()

    stable = optimizer.recommend(
        {
            "workload": "market_execution",
            "latency_ms": 120.0,
            "error_rate": 0.01,
            "volatility": 0.4,
        }
    )
    assert stable["recommended_mode"] == "direct"

    unstable = optimizer.recommend(
        {
            "workload": "market_execution",
            "latency_ms": 480.0,
            "error_rate": 0.2,
            "volatility": 0.8,
        }
    )
    assert unstable["recommended_mode"] == "vpn"


def test_transport_optimizer_can_recommend_tor_for_research() -> None:
    optimizer = TransportOptimizer()
    out = optimizer.recommend(
        {
            "workload": "research",
            "latency_ms": 150.0,
            "error_rate": 0.01,
            "volatility": 0.1,
        }
    )
    assert out["recommended_mode"] == "tor"
    assert 0.0 <= float(out["confidence_score"]) <= 1.0
