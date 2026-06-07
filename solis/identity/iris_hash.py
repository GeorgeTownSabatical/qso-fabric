from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class IrisHashRecord:
    template_hash: str
    kdf: str
    rounds: int


def _normalize_template(template: bytes) -> bytes:
    if not isinstance(template, (bytes, bytearray)):
        raise TypeError("template must be bytes")
    if len(template) < 16:
        raise ValueError("template bytes too short")
    return bytes(template)


def hash_iris_template(template: bytes, *, salt: bytes, rounds: int = 3) -> IrisHashRecord:
    """Deterministic iris template hashing abstraction.

    This function intentionally accepts only pre-derived feature bytes and never
    raw image payloads.
    """

    tpl = _normalize_template(template)
    if not isinstance(salt, (bytes, bytearray)) or len(salt) < 8:
        raise ValueError("salt must be bytes with len >= 8")

    digest = tpl + bytes(salt)
    for _ in range(rounds):
        digest = hashlib.sha3_512(digest).digest()

    return IrisHashRecord(
        template_hash=digest.hex(),
        kdf="argon2id-compatible-stub",
        rounds=rounds,
    )
