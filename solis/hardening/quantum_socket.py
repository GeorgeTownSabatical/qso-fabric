from __future__ import annotations

import hashlib
import json
import ssl
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from solis.anchor.eth_anchor import EthereumAnchor
from solis.identity.pq_keys import generate_keypair, sign, verify


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha384(payload: Mapping[str, Any]) -> str:
    return hashlib.sha384(canonical_json(payload).encode("utf-8")).hexdigest()


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def build_tls_context(tls_cert: str | None, tls_key: str | None) -> ssl.SSLContext | None:
    cert = (tls_cert or "").strip()
    key = (tls_key or "").strip()
    if not cert and not key:
        return None
    if not cert or not key:
        raise ValueError("both tls_cert and tls_key are required to enable TLS")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=cert, keyfile=key)
    return context


@dataclass(frozen=True)
class QuantumSocketSigner:
    private_key_hex: str
    signature_algo: str = "ML-DSA-65"
    kem_algo: str = "ML-KEM-768"
    crypto_profile_id: str = "X25519+ML-KEM-768/ML-DSA-65"

    @classmethod
    def from_seed_hex(
        cls,
        seed_hex: str,
        *,
        signature_algo: str = "ML-DSA-65",
        kem_algo: str = "ML-KEM-768",
        crypto_profile_id: str = "X25519+ML-KEM-768/ML-DSA-65",
    ) -> "QuantumSocketSigner":
        seed = bytes.fromhex(seed_hex.strip())
        keypair = generate_keypair(seed, signature_algo=signature_algo, kem_algo=kem_algo)
        return cls(
            private_key_hex=keypair.private_key,
            signature_algo=signature_algo,
            kem_algo=kem_algo,
            crypto_profile_id=crypto_profile_id,
        )

    def sign_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        canonical = canonical_json(payload).encode("utf-8")
        payload_hash = canonical_sha384(payload)
        signature = sign(canonical, self.private_key_hex)
        return {
            "crypto_profile_id": self.crypto_profile_id,
            "signature_algo": self.signature_algo,
            "kem_algo": self.kem_algo,
            "payload_hash_sha384": payload_hash,
            "signature": signature,
        }

    def verify_payload(self, payload: Mapping[str, Any], envelope: Mapping[str, Any]) -> bool:
        expected_hash = canonical_sha384(payload)
        supplied_hash = str(envelope.get("payload_hash_sha384", "")).strip().lower()
        if supplied_hash != expected_hash:
            return False
        signature = str(envelope.get("signature", "")).strip()
        if not signature:
            return False
        canonical = canonical_json(payload).encode("utf-8")
        return bool(verify(canonical, signature, self.private_key_hex))


class EthereumAnchorProtocol(Protocol):
    def anchor(self, merkle_root: str, *, deterministic_mode: bool = False): ...


@dataclass(frozen=True)
class SocketAnchorReceipt:
    contract_address: str
    merkle_root: str
    tx_hash: str
    mode: str
    chain_id: int | None
    metadata: dict[str, Any]


class SolidityAnchorSocketLedger:
    def __init__(
        self,
        *,
        contract_address: str,
        rpc_url: str | None = None,
        private_key: str | None = None,
        deterministic_mode: bool = True,
        anchor_adapter: EthereumAnchorProtocol | None = None,
    ) -> None:
        contract = str(contract_address).strip()
        if not contract:
            raise ValueError("contract_address is required")

        self.contract_address = contract
        self.deterministic_mode = bool(deterministic_mode)

        if anchor_adapter is not None:
            self._anchor_adapter: EthereumAnchorProtocol | None = anchor_adapter
        elif (rpc_url or "").strip() and (private_key or "").strip():
            self._anchor_adapter = EthereumAnchor(
                rpc_url=str(rpc_url),
                contract_address=self.contract_address,
                private_key=str(private_key),
            )
        else:
            self._anchor_adapter = None

    def anchor_payload(self, payload: Mapping[str, Any]) -> SocketAnchorReceipt:
        root_hex = "0x" + canonical_sha256(payload)
        if self._anchor_adapter is None:
            tx_hash = "0x" + hashlib.sha256(f"{self.contract_address}:{root_hex}".encode("utf-8")).hexdigest()
            return SocketAnchorReceipt(
                contract_address=self.contract_address,
                merkle_root=root_hex,
                tx_hash=tx_hash,
                mode="local_deterministic",
                chain_id=None,
                metadata={"deterministic_mode": True},
            )

        result = self._anchor_adapter.anchor(root_hex, deterministic_mode=self.deterministic_mode)
        metadata_obj = getattr(result, "metadata", None)
        metadata = dict(vars(metadata_obj)) if metadata_obj is not None else {}
        mode = "ethereum_deterministic" if self.deterministic_mode else "ethereum_live"
        return SocketAnchorReceipt(
            contract_address=self.contract_address,
            merkle_root=str(getattr(result, "merkle_root", root_hex)),
            tx_hash=str(getattr(result, "tx_hash", "")),
            mode=mode,
            chain_id=int(getattr(result, "chain_id", 0)) if getattr(result, "chain_id", None) is not None else None,
            metadata=metadata,
        )

