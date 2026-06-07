from __future__ import annotations

from observability.dashboards import build_solis_telemetry_dashboards
from solis.telemetry import ExecutionTelemetryEvent


def _event(
    event_id: str,
    *,
    strategy_id: str,
    venue: str,
    latency_ms: int,
    slippage_bps: float,
    reject_rate: float,
    model_drift_score: float,
    metric_ts: str,
    anomaly_flags: list[str],
) -> ExecutionTelemetryEvent:
    return ExecutionTelemetryEvent.model_validate(
        {
            "schema_version": "1.0",
            "event_id": event_id,
            "intent_id": "intent-01",
            "strategy_id": strategy_id,
            "venue": venue,
            "symbol": "AAPL",
            "metric_ts": metric_ts,
            "latency_ms": latency_ms,
            "slippage_bps": slippage_bps,
            "reject_rate": reject_rate,
            "model_drift_score": model_drift_score,
            "anomaly_flags": anomaly_flags,
        }
    )


def test_dashboard_maps_execution_quality_and_drift_by_strategy_and_venue() -> None:
    events = [
        _event(
            "evt-1",
            strategy_id="mean_reversion",
            venue="alpaca",
            latency_ms=20,
            slippage_bps=0.8,
            reject_rate=0.0,
            model_drift_score=0.10,
            metric_ts="2026-02-25T00:00:00+00:00",
            anomaly_flags=["none"],
        ),
        _event(
            "evt-2",
            strategy_id="mean_reversion",
            venue="alpaca",
            latency_ms=30,
            slippage_bps=1.0,
            reject_rate=0.1,
            model_drift_score=0.25,
            metric_ts="2026-02-25T00:00:03+00:00",
            anomaly_flags=["drift_warn"],
        ),
        _event(
            "evt-3",
            strategy_id="momentum",
            venue="alpaca",
            latency_ms=40,
            slippage_bps=1.2,
            reject_rate=0.0,
            model_drift_score=0.20,
            metric_ts="2026-02-25T00:00:02+00:00",
            anomaly_flags=["none"],
        ),
        _event(
            "evt-4",
            strategy_id="momentum",
            venue="broker-x",
            latency_ms=10,
            slippage_bps=0.6,
            reject_rate=0.0,
            model_drift_score=0.05,
            metric_ts="2026-02-25T00:00:01+00:00",
            anomaly_flags=["none"],
        ),
    ]

    dashboard = build_solis_telemetry_dashboards(events)

    assert dashboard["schema_version"] == "1.0"
    assert dashboard["dashboard_id"] == "solis_execution_quality_v1"
    assert dashboard["window_start"] == "2026-02-25T00:00:00+00:00"
    assert dashboard["window_end"] == "2026-02-25T00:00:03+00:00"

    global_quality = dashboard["execution_quality"]["global"]
    assert global_quality["event_count"] == 4
    assert global_quality["latency_ms_avg"] == 25.0
    assert global_quality["slippage_bps_avg"] == 0.9
    assert global_quality["reject_rate_avg"] == 0.025

    strategy_rows = dashboard["execution_quality"]["by_strategy"]
    assert [row["strategy_id"] for row in strategy_rows] == ["mean_reversion", "momentum"]
    assert strategy_rows[0]["event_count"] == 2
    assert strategy_rows[0]["latency_ms_avg"] == 25.0
    assert strategy_rows[1]["event_count"] == 2
    assert strategy_rows[1]["latency_ms_avg"] == 25.0

    venue_rows = dashboard["execution_quality"]["by_venue"]
    assert [row["venue"] for row in venue_rows] == ["alpaca", "broker-x"]
    assert venue_rows[0]["event_count"] == 3
    assert venue_rows[1]["event_count"] == 1

    strategy_venue_rows = dashboard["execution_quality"]["by_strategy_venue"]
    assert [(row["strategy_id"], row["venue"]) for row in strategy_venue_rows] == [
        ("mean_reversion", "alpaca"),
        ("momentum", "alpaca"),
        ("momentum", "broker-x"),
    ]

    global_drift = dashboard["model_drift"]["global"]
    assert global_drift["model_drift_avg"] == 0.15
    assert global_drift["anomaly_flag_counts"]["drift_warn"] == 1


def test_dashboard_output_is_deterministic_for_reordered_input() -> None:
    base = [
        _event(
            "evt-a",
            strategy_id="a",
            venue="alpaca",
            latency_ms=10,
            slippage_bps=1.0,
            reject_rate=0.0,
            model_drift_score=0.2,
            metric_ts="2026-02-25T00:00:01+00:00",
            anomaly_flags=[],
        ),
        _event(
            "evt-b",
            strategy_id="b",
            venue="broker-x",
            latency_ms=30,
            slippage_bps=2.0,
            reject_rate=0.2,
            model_drift_score=0.4,
            metric_ts="2026-02-25T00:00:00+00:00",
            anomaly_flags=["drift_warn"],
        ),
    ]

    first = build_solis_telemetry_dashboards(base)
    second = build_solis_telemetry_dashboards(reversed(base))
    assert first == second
