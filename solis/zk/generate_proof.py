from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from solis.services.solis_star_service import SolisQSOBridge
from solis.zk.command_adapter import CircomSnarkjsAdapter, ZKCommandConfig


def compute_collapse(entropy: float, magnetic: float, fusion: float) -> float:
    raw = entropy * (1.0 - magnetic) * fusion
    if raw < 0.0:
        return 0.0
    if raw > 1.0:
        return 1.0
    return raw


def generate_collapse_proof(
    *,
    epoch: int,
    entropy: float,
    magnetic: float,
    fusion: float,
    threshold: float,
    qso: SolisQSOBridge | None = None,
    command_config: ZKCommandConfig | None = None,
) -> Dict[str, Any]:
    collapse_probability = compute_collapse(entropy, magnetic, fusion)
    statement_ok = collapse_probability <= threshold

    payload = {
        "epoch": epoch,
        "entropy": entropy,
        "magnetic": magnetic,
        "fusion": fusion,
        "collapse_probability": collapse_probability,
        "threshold": threshold,
        "statement_ok": statement_ok,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    proof_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    proof = {
        **payload,
        "proof_hash": proof_hash,
        "scheme": "deterministic-hash-stub",
    }

    command_adapter = CircomSnarkjsAdapter(command_config)
    command_artifacts = command_adapter.prove(
        epoch=epoch,
        entropy=entropy,
        magnetic=magnetic,
        fusion=fusion,
    )
    if command_artifacts is not None:
        proof["scheme"] = "circom-snarkjs"
        proof["artifacts"] = command_artifacts

    if qso is not None:
        uri = f"qso://solis.zkproof.{epoch}"
        if not qso.has(uri):
            qso.create(uri, {"type": "solis_zk_proof"})
        qso.patch(uri, proof, actor="solis.zk", policy_version="v1", node_id="solis")

    return proof
