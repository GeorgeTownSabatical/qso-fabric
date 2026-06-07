from __future__ import annotations

from solis.identity.zk.proof_adapter import CollapseProof
from solis.physics.collapse_engine import collapse_probability_v1
from solis.physics.fixed_math import Fixed64
from solis.shared.hashing import sha256_hex_obj


def verify_collapse_proof(proof: CollapseProof) -> bool:
    entropy = Fixed64.from_str(proof.entropy)
    magnetic = Fixed64.from_str(proof.magnetic)
    fusion = Fixed64.from_str(proof.fusion)
    threshold = Fixed64.from_str(proof.threshold)
    collapse = collapse_probability_v1(entropy, magnetic, fusion)

    expected_payload = {
        "entropy": entropy.to_raw(),
        "magnetic": magnetic.to_raw(),
        "fusion": fusion.to_raw(),
        "collapse_probability": collapse.to_raw(),
        "threshold": threshold.to_raw(),
        "statement_ok": collapse <= threshold,
    }
    return proof.proof_hash == sha256_hex_obj(expected_payload)
