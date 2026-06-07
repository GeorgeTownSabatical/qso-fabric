from __future__ import annotations

import pytest

from solis.governance import (
    GovernorDecision,
    GovernorDecisionKind,
    InvariantTraceRow,
    decision_replay_record,
    enforce_signed_governor_decision,
)
from solis.shared.hashing import sha256_hex_text


def _base_decision(*, signature: str = "") -> GovernorDecision:
    return GovernorDecision(
        decision_id="dec-sig-1",
        decision_ts="2026-02-25T00:00:00+00:00",
        intent_id="intent-01",
        decision=GovernorDecisionKind.APPROVED_EXECUTE,
        reason_codes=["OK"],
        invariant_trace=[InvariantTraceRow(name="risk_limit", status="PASS", detail="within range")],
        policy_version="v1",
        actor="governor://engine",
        signature=signature,
    )


def test_unsigned_governance_decision_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsigned governance decision rejected"):
        enforce_signed_governor_decision(_base_decision(signature=""))


def test_signed_governance_decision_produces_replay_metadata() -> None:
    signed = _base_decision().sign(lambda payload: f"sig:{sha256_hex_text(payload)[:12]}")
    checked = enforce_signed_governor_decision(
        signed,
        verifier=lambda payload, signature: signature == f"sig:{sha256_hex_text(payload)[:12]}",
    )
    assert checked.decision_hash == signed.compute_hash()

    replay = decision_replay_record(checked)
    assert replay["signature_metadata"]["signature_present"] is True
    assert replay["signature_metadata"]["signature_length"] > 0
    assert replay["signature_metadata"]["decision_hash"] == checked.decision_hash


def test_governance_decision_hash_mismatch_is_rejected() -> None:
    signed = _base_decision().sign(lambda payload: f"sig:{sha256_hex_text(payload)[:12]}")
    tampered = signed.model_copy(update={"decision_hash": "0" * 64})
    with pytest.raises(ValueError, match="hash mismatch"):
        enforce_signed_governor_decision(tampered)
