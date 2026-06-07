from __future__ import annotations

from dataclasses import dataclass

import pytest

from solis.identity.pq_keys import nist_primitives_available
from solis.hardening.quantum_socket import (
    QuantumSocketSigner,
    SolidityAnchorSocketLedger,
    build_tls_context,
)


def test_build_tls_context_none_when_unconfigured() -> None:
    assert build_tls_context(None, None) is None


def test_build_tls_context_requires_both_paths() -> None:
    with pytest.raises(ValueError):
        build_tls_context("cert.pem", None)
    with pytest.raises(ValueError):
        build_tls_context(None, "key.pem")


def test_quantum_socket_signer_round_trip_verification() -> None:
    if not nist_primitives_available():
        pytest.skip("liboqs ML-KEM/ML-DSA primitives are not available in this environment")

    signer = QuantumSocketSigner.from_seed_hex("ab" * 32)
    payload = {"type": "tail", "conversation_id": "main", "limit": 20}
    envelope = signer.sign_payload(payload)
    assert envelope["signature_algo"] == "ML-DSA-65"
    assert envelope["kem_algo"] == "ML-KEM-768"
    assert signer.verify_payload(payload, envelope)

    tampered = {"type": "tail", "conversation_id": "main", "limit": 21}
    assert not signer.verify_payload(tampered, envelope)


def test_solidity_anchor_socket_ledger_local_deterministic_mode() -> None:
    ledger = SolidityAnchorSocketLedger(contract_address="0xabc")
    payload = {"type": "tail", "session_token": "demo", "limit": 20}

    out_1 = ledger.anchor_payload(payload)
    out_2 = ledger.anchor_payload(payload)

    assert out_1.contract_address == "0xabc"
    assert out_1.mode == "local_deterministic"
    assert out_1.merkle_root == out_2.merkle_root
    assert out_1.tx_hash == out_2.tx_hash


@dataclass
class _FakeAnchorResult:
    merkle_root: str
    tx_hash: str
    chain_id: int
    metadata: object


@dataclass
class _FakeAnchorMetadata:
    deterministic_mode: bool


class _FakeAnchorAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bool]] = []

    def anchor(self, merkle_root: str, *, deterministic_mode: bool = False) -> _FakeAnchorResult:
        self.calls.append((merkle_root, deterministic_mode))
        return _FakeAnchorResult(
            merkle_root=merkle_root,
            tx_hash="0xfakehash",
            chain_id=31337,
            metadata=_FakeAnchorMetadata(deterministic_mode=deterministic_mode),
        )


def test_solidity_anchor_socket_ledger_uses_adapter_when_supplied() -> None:
    adapter = _FakeAnchorAdapter()
    ledger = SolidityAnchorSocketLedger(
        contract_address="0xdef",
        deterministic_mode=False,
        anchor_adapter=adapter,
    )
    out = ledger.anchor_payload({"x": 1})
    assert out.contract_address == "0xdef"
    assert out.mode == "ethereum_live"
    assert out.tx_hash == "0xfakehash"
    assert out.chain_id == 31337
    assert adapter.calls
    assert adapter.calls[0][1] is False
