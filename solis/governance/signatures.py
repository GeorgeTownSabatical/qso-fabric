from __future__ import annotations

from typing import Any, Callable

from solis.governance.decision import GovernorDecision
from solis.shared.canonical_json import canonical_json


def enforce_signed_governor_decision(
    decision: GovernorDecision,
    *,
    verifier: Callable[[str, str], bool] | None = None,
) -> GovernorDecision:
    signature = decision.signature.strip()
    if not signature:
        raise ValueError("unsigned governance decision rejected")

    expected_hash = decision.compute_hash()
    if decision.decision_hash is not None and decision.decision_hash != expected_hash:
        raise ValueError("governance decision hash mismatch")

    payload = decision.canonical_payload()
    payload_text = canonical_json(payload)
    if verifier is not None and not verifier(payload_text, signature):
        raise ValueError("governance signature verification failed")

    return decision.model_copy(update={"decision_hash": expected_hash})


def decision_replay_record(
    decision: GovernorDecision,
    *,
    verifier: Callable[[str, str], bool] | None = None,
) -> dict[str, Any]:
    signed = enforce_signed_governor_decision(decision, verifier=verifier)
    base = signed.model_dump(mode="json")
    base["signature_metadata"] = {
        "signature_present": bool(signed.signature.strip()),
        "signature_length": len(signed.signature),
        "decision_hash": signed.decision_hash,
    }
    return base
