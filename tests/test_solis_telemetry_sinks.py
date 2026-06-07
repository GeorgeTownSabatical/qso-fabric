from __future__ import annotations

from api.mcp_tools.qso_tools import QSOMCPTools
from solis.telemetry import (
    BoundedMemorySink,
    ExecutionTelemetryEvent,
    QSOTelemetrySink,
    TelemetryDispatcher,
    validate_execution_telemetry_event,
)


def _event(event_id: str, *, latency_ms: int = 25) -> ExecutionTelemetryEvent:
    return validate_execution_telemetry_event(
        {
            "schema_version": "1.0",
            "event_id": event_id,
            "intent_id": "intent-01",
            "strategy_id": "strategy-momentum",
            "venue": "alpaca",
            "symbol": "aapl",
            "metric_ts": "2026-02-25T00:00:00+00:00",
            "latency_ms": latency_ms,
            "slippage_bps": 1.2,
            "reject_rate": 0.0,
            "model_drift_score": 0.05,
            "anomaly_flags": [],
        }
    )


def test_qso_telemetry_sink_emits_hashed_deterministic_payload() -> None:
    tools = QSOMCPTools()
    sink = QSOTelemetrySink(tools=tools)
    event = _event("telemetry-1")
    hashed = event.with_hash()

    uri_a = sink.emit(event)
    uri_b = sink.emit(event)

    assert uri_a == uri_b
    assert uri_a == "qso://solis.telemetry.telemetry-1"

    current = tools.qso_read(uri_a)
    assert current["state_layer"]["event_id"] == "telemetry-1"
    assert current["state_layer"]["symbol"] == "AAPL"
    assert current["state_layer"]["event_hash"] == hashed.event_hash

    timeline = tools.qso_timeline(uri_a)
    assert len(timeline) == 2
    assert timeline[0]["delta"]["event_hash"] == hashed.event_hash
    assert timeline[1]["delta"]["event_hash"] == hashed.event_hash


def test_bounded_memory_sink_is_bounded_and_drain_clears() -> None:
    sink = BoundedMemorySink(max_events=2)
    sink.emit(_event("telemetry-1"))
    sink.emit(_event("telemetry-2"))
    sink.emit(_event("telemetry-3"))

    drained = sink.drain()
    assert [row["event_id"] for row in drained] == ["telemetry-2", "telemetry-3"]
    assert sink.drain() == []


def test_dispatcher_is_non_blocking_for_optional_sink_failures() -> None:
    tools = QSOMCPTools()
    qso_sink = QSOTelemetrySink(tools=tools)
    recorder = BoundedMemorySink(max_events=8)

    class _FailingSink:
        def emit(self, event: ExecutionTelemetryEvent) -> None:
            _ = event
            raise RuntimeError("optional sink down")

    dispatcher = TelemetryDispatcher(
        qso_sink=qso_sink,
        optional_sinks=[_FailingSink(), recorder],
    )

    event = _event("telemetry-4")
    uri = dispatcher.emit(event)

    assert uri == "qso://solis.telemetry.telemetry-4"
    assert tools.runtime.registry.has(uri)

    timeline = tools.qso_timeline(uri)
    assert len(timeline) == 1
    assert timeline[0]["delta"]["event_id"] == "telemetry-4"

    drained = recorder.drain()
    assert len(drained) == 1
    assert drained[0]["event_id"] == "telemetry-4"
