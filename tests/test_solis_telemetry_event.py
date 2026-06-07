from __future__ import annotations

from solis.shared.hashing import sha256_hex_obj
from solis.telemetry import (
    ExecutionTelemetryEvent,
    load_execution_telemetry_schema,
    validate_execution_telemetry_event,
)


def _payload(event_id: str, latency_ms: int) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": event_id,
        "intent_id": "intent-01",
        "strategy_id": "strategy-mean-revert",
        "venue": "alpaca",
        "symbol": "aapl",
        "metric_ts": "2026-02-25T00:00:00+00:00",
        "latency_ms": latency_ms,
        "slippage_bps": 1.25,
        "reject_rate": 0.0,
        "model_drift_score": 0.13,
        "anomaly_flags": ["none"],
    }


def test_execution_telemetry_event_is_versioned_and_hashable() -> None:
    event = validate_execution_telemetry_event(_payload("telemetry-1", 42))
    assert isinstance(event, ExecutionTelemetryEvent)
    assert event.schema_version == "1.0"
    assert event.symbol == "AAPL"

    hashed = event.with_hash()
    assert hashed.event_hash == event.compute_hash()
    assert hashed.event_hash == event.compute_hash()


def test_execution_telemetry_schema_contract() -> None:
    schema = load_execution_telemetry_schema()
    assert schema["additionalProperties"] is False
    required = set(schema["required"])
    assert {
        "schema_version",
        "event_id",
        "intent_id",
        "strategy_id",
        "venue",
        "symbol",
        "metric_ts",
        "latency_ms",
        "slippage_bps",
        "reject_rate",
        "model_drift_score",
        "anomaly_flags",
    }.issubset(required)


def test_execution_telemetry_events_replay_with_stable_hash_chain() -> None:
    events = [
        validate_execution_telemetry_event(_payload("telemetry-1", 42)).with_hash(),
        validate_execution_telemetry_event(_payload("telemetry-2", 55)).with_hash(),
    ]
    payloads = [event.model_dump(mode="json") for event in events]
    first_hash = sha256_hex_obj(payloads)
    second_hash = sha256_hex_obj(payloads)
    assert first_hash == second_hash
