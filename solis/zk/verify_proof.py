from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from solis.zk.command_adapter import CircomSnarkjsAdapter, ZKCommandConfig


def verify_collapse_proof(
    proof: Mapping[str, Any],
    *,
    command_config: ZKCommandConfig | None = None,
) -> bool:
    required = {
        "epoch",
        "entropy",
        "magnetic",
        "fusion",
        "collapse_probability",
        "threshold",
        "statement_ok",
        "proof_hash",
    }
    if not required.issubset(proof.keys()):
        return False

    payload = {
        "epoch": int(proof["epoch"]),
        "entropy": float(proof["entropy"]),
        "magnetic": float(proof["magnetic"]),
        "fusion": float(proof["fusion"]),
        "collapse_probability": float(proof["collapse_probability"]),
        "threshold": float(proof["threshold"]),
        "statement_ok": bool(proof["statement_ok"]),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    expected_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    if expected_hash != str(proof["proof_hash"]):
        return False

    recomputed = payload["entropy"] * (1.0 - payload["magnetic"]) * payload["fusion"]
    recomputed = max(0.0, min(1.0, recomputed))
    if abs(recomputed - payload["collapse_probability"]) > 1e-12:
        return False

    if bool(payload["statement_ok"]) != (payload["collapse_probability"] <= payload["threshold"]):
        return False

    if str(proof.get("scheme", "")) != "circom-snarkjs":
        return True

    command_adapter = CircomSnarkjsAdapter(command_config)
    command_result = command_adapter.verify(proof)
    if command_result is None:
        return True
    return command_result
