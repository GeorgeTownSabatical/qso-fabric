from __future__ import annotations

from dataclasses import dataclass

from solis.physics.collapse_engine import collapse_probability_v1
from solis.physics.fixed_math import Fixed64
from solis.shared.hashing import sha256_hex_obj


@dataclass(frozen=True)
class CollapseProof:
    proof_hash: str
    entropy: str
    magnetic: str
    fusion: str
    collapse_probability: str
    threshold: str
    statement_ok: bool


def generate_collapse_proof(
    *,
    entropy: Fixed64,
    magnetic: Fixed64,
    fusion: Fixed64,
    threshold: Fixed64,
) -> CollapseProof:
    collapse = collapse_probability_v1(entropy, magnetic, fusion)
    statement_ok = collapse <= threshold

    payload = {
        "entropy": entropy.to_raw(),
        "magnetic": magnetic.to_raw(),
        "fusion": fusion.to_raw(),
        "collapse_probability": collapse.to_raw(),
        "threshold": threshold.to_raw(),
        "statement_ok": statement_ok,
    }
    proof_hash = sha256_hex_obj(payload)

    return CollapseProof(
        proof_hash=proof_hash,
        entropy=entropy.to_str(18),
        magnetic=magnetic.to_str(18),
        fusion=fusion.to_str(18),
        collapse_probability=collapse.to_str(18),
        threshold=threshold.to_str(18),
        statement_ok=statement_ok,
    )
