from __future__ import annotations

import pytest

from solis.governance import (
    GovernorDecision,
    GovernorDecisionKind,
    InvariantTraceRow,
    load_governor_decision_schema,
    validate_governor_decision,
)
from solis.shared.hashing import sha256_hex_obj


def _payload(decision: str) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "decision_id": "dec-001",
        "decision_ts": "2026-02-25T00:00:00+00:00",
        "intent_id": "intent-001",
        "decision": decision,
        "reason_codes": ["OK"] if decision != "REJECTED" else ["RISK_LIMIT_HIT"],
        "invariant_trace": [{"name": "max_drawdown", "status": "PASS", "detail": "within_limit"}],
        "policy_version": "v1",
        "actor": "governor://engine",
        "signature": "placeholder",
    }


def test_governor_decision_is_signed_and_hashable() -> None:
    decision = validate_governor_decision(_payload("APPROVED_SHADOW"))
    signed = decision.sign(lambda payload: f"sig:{len(payload)}")
    assert isinstance(signed, GovernorDecision)
    assert signed.decision == GovernorDecisionKind.APPROVED_SHADOW
    assert signed.decision_hash == decision.compute_hash()
    assert signed.signature.startswith("sig:")


def test_governor_decision_rejected_requires_reason_codes() -> None:
    payload = _payload("REJECTED")
    payload["reason_codes"] = []
    with pytest.raises(ValueError, match="reason_codes"):
        validate_governor_decision(payload)


def test_governor_decision_schema_contract() -> None:
    schema = load_governor_decision_schema()
    assert schema["additionalProperties"] is False
    required = set(schema["required"])
    assert {
        "schema_version",
        "decision_id",
        "decision_ts",
        "intent_id",
        "decision",
        "reason_codes",
        "invariant_trace",
        "policy_version",
        "actor",
        "signature",
    }.issubset(required)
    assert set(schema["properties"]["decision"]["enum"]) == {
        "REJECTED",
        "APPROVED_SHADOW",
        "APPROVED_EXECUTE",
    }


def test_governor_decision_replay_hash_is_deterministic() -> None:
    row = InvariantTraceRow(name="liquidity", status="PASS", detail="sufficient")
    decisions = [
        GovernorDecision(
            decision_id="dec-001",
            decision_ts="2026-02-25T00:00:00+00:00",
            intent_id="intent-001",
            decision=GovernorDecisionKind.APPROVED_EXECUTE,
            reason_codes=["OK"],
            invariant_trace=[row],
            policy_version="v1",
            actor="governor://engine",
            signature="sig",
        ).model_dump(mode="json"),
        GovernorDecision(
            decision_id="dec-002",
            decision_ts="2026-02-25T00:00:01+00:00",
            intent_id="intent-002",
            decision=GovernorDecisionKind.REJECTED,
            reason_codes=["VOLATILITY_SPIKE"],
            invariant_trace=[row],
            policy_version="v1",
            actor="governor://engine",
            signature="sig",
        ).model_dump(mode="json"),
    ]
    assert sha256_hex_obj(decisions) == sha256_hex_obj(decisions)
