from __future__ import annotations

import pytest

from solis.execution import FORBIDDEN_ORDER_FIELDS, load_execution_intent_schema, validate_execution_intent


def _valid_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "intent_id": "intent-001",
        "strategy_id": "momentum-v1",
        "as_of_ts": "2026-02-25T00:00:00+00:00",
        "symbol_set": ["aapl", "msft", "AAPL"],
        "requested_exposure_delta_bps": 75,
        "horizon_ms": 900000,
        "confidence": 0.82,
        "model_version": "1.2",
        "features_commit_hash": "a" * 40,
        "compiler_version": "1.0",
        "policy_version": "v1",
        "risk_hints": ["liquid_equity"],
    }


def test_execution_intent_accepts_valid_payload_and_normalizes_symbols() -> None:
    intent = validate_execution_intent(_valid_payload())
    assert intent.symbol_set == ["AAPL", "MSFT"]
    assert intent.requested_exposure_delta_bps == 75
    assert intent.confidence == 0.82


def test_execution_intent_rejects_direct_order_authority_fields() -> None:
    payload = _valid_payload()
    payload["side"] = "buy"
    with pytest.raises(ValueError, match="direct order fields"):
        validate_execution_intent(payload)


def test_execution_intent_rejects_out_of_bounds_confidence_and_exposure() -> None:
    payload = _valid_payload()
    payload["confidence"] = 1.5
    with pytest.raises(ValueError):
        validate_execution_intent(payload)

    payload = _valid_payload()
    payload["requested_exposure_delta_bps"] = 20000
    with pytest.raises(ValueError):
        validate_execution_intent(payload)


def test_execution_intent_schema_contract_blocks_unmodeled_order_fields() -> None:
    schema = load_execution_intent_schema()
    assert schema["additionalProperties"] is False
    required = set(schema["required"])
    assert {
        "schema_version",
        "intent_id",
        "strategy_id",
        "as_of_ts",
        "symbol_set",
        "requested_exposure_delta_bps",
        "horizon_ms",
        "confidence",
        "model_version",
        "features_commit_hash",
    }.issubset(required)
    for field in FORBIDDEN_ORDER_FIELDS:
        assert field not in schema["properties"]
