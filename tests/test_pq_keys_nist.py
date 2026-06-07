from __future__ import annotations

import hashlib

import pytest

from solis.identity.pq_keys import generate_keypair, nist_primitives_available, sign, verify


def test_nist_keypair_and_signature_roundtrip() -> None:
    if not nist_primitives_available():
        pytest.skip("liboqs ML-KEM/ML-DSA primitives are not available in this environment")

    kp = generate_keypair(b"seed-seed-seed-seed")
    assert kp.public_key.startswith("pqv2:")
    assert kp.private_key.startswith("pqv2:")

    signature = sign(b"hello", kp.private_key)
    assert signature.startswith("pqsigv2:")
    assert verify(b"hello", signature, kp.private_key)
    assert not verify(b"hello!", signature, kp.private_key)


def test_legacy_hmac_signature_path_is_blocked_fail_closed() -> None:
    private_key_hex = hashlib.sha3_512(b"legacy-key").hexdigest()
    with pytest.raises(ValueError):
        sign(b"legacy", private_key_hex)
    assert not verify(b"legacy", "deadbeef", private_key_hex)
