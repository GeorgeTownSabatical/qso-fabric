from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass
class SphereChainAnchorResult:
    merkle_root: str
    receipt_id: str
    tx_hash: str
    metadata: SphereChainAnchorMetadata


@dataclass(frozen=True)
class SphereChainSignedTransaction:
    raw_transaction: bytes
    tx_hash: str


class SphereChainClient(Protocol):
    def derive_address(self, private_key: str) -> str:
        ...

    def build_anchor_transaction(
        self,
        *,
        contract_address: str,
        merkle_root: str,
        chain_id: int,
        nonce: int,
        gas: int,
        gas_price: int,
        value: int,
        sender: str,
    ) -> dict[str, Any]:
        ...

    def sign_transaction(self, transaction: Mapping[str, Any], private_key: str) -> SphereChainSignedTransaction:
        ...

    def submit_raw_transaction(self, raw_transaction: bytes) -> str:
        ...

    def get_transaction_receipt(self, tx_hash: str) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class SphereChainAnchorMetadata:
    endpoint: str
    contract_address: str
    sender: str
    chain_id: int
    nonce: int
    gas: int
    gas_price: int
    value: int
    signed_tx_hash: str
    receipt_status: str
    receipt_block_number: int
    deterministic_mode: bool


class DeterministicSphereChainClient:
    """Deterministic fallback client that keeps network behavior injectable."""

    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    def derive_address(self, private_key: str) -> str:
        digest = hashlib.sha256(f"addr:{private_key}".encode("utf-8")).hexdigest()[:40]
        return "0x" + digest

    def build_anchor_transaction(
        self,
        *,
        contract_address: str,
        merkle_root: str,
        chain_id: int,
        nonce: int,
        gas: int,
        gas_price: int,
        value: int,
        sender: str,
    ) -> dict[str, Any]:
        return {
            "type": "anchorRoot",
            "method": "anchorRoot",
            "contract": contract_address,
            "params": {"root": merkle_root},
            "chain_id": chain_id,
            "nonce": nonce,
            "gas": gas,
            "gas_price": gas_price,
            "value": value,
            "from": sender,
            "endpoint": self.endpoint,
        }

    def sign_transaction(self, transaction: Mapping[str, Any], private_key: str) -> SphereChainSignedTransaction:
        canonical_tx = json.dumps(dict(transaction), sort_keys=True, separators=(",", ":"))
        signature = hashlib.sha256(f"{private_key}:{canonical_tx}".encode("utf-8")).hexdigest()
        envelope = {"tx": dict(transaction), "signature": signature}
        raw_transaction = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        tx_hash = "0x" + hashlib.sha256(raw_transaction).hexdigest()
        return SphereChainSignedTransaction(raw_transaction=raw_transaction, tx_hash=tx_hash)

    def submit_raw_transaction(self, raw_transaction: bytes) -> str:
        return "0x" + hashlib.sha256(raw_transaction).hexdigest()

    def get_transaction_receipt(self, tx_hash: str) -> Mapping[str, Any]:
        normalized_hash = _normalize_hex(tx_hash)
        block_number = int(normalized_hash[2:10], 16)
        return {
            "transaction_hash": normalized_hash,
            "status": "committed",
            "block_number": block_number,
        }


def _normalize_hex(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    text = str(value).strip().lower()
    if text.startswith("0x"):
        return text
    return "0x" + text


def _normalize_merkle_root(merkle_root: str) -> str:
    root = merkle_root.strip().lower()
    if root.startswith("0x"):
        root = root[2:]
    if len(root) != 64:
        raise ValueError("merkle_root must be a 32-byte hex string")
    try:
        bytes.fromhex(root)
    except ValueError as exc:
        raise ValueError("merkle_root must be a 32-byte hex string") from exc
    return "0x" + root


def _to_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _deterministic_receipt_id(tx_hash: str, status: str, block_number: int) -> str:
    payload = f"{tx_hash}:{status}:{block_number}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class SphereChainAnchor:
    """SphereChain anchoring adapter with signed transaction submission."""

    def __init__(
        self,
        endpoint: str,
        private_key: str = "spherechain-deterministic-key",
        contract_address: str = "spherechain-anchor",
        *,
        client: SphereChainClient | None = None,
        deterministic_chain_id: int = 13_337,
        deterministic_nonce: int = 0,
    ) -> None:
        self.endpoint = endpoint
        self.private_key = private_key
        self.contract_address = contract_address
        self._client = client or DeterministicSphereChainClient(endpoint)
        self._deterministic_chain_id = deterministic_chain_id
        self._deterministic_nonce = deterministic_nonce

    def anchor(
        self,
        merkle_root: str,
        *,
        chain_id: int | None = None,
        nonce: int | None = None,
        gas: int = 300_000,
        gas_price: int = 1_000_000_000,
        deterministic_mode: bool = False,
    ) -> SphereChainAnchorResult:
        normalized_root = _normalize_merkle_root(merkle_root)
        sender = self._client.derive_address(self.private_key)
        resolved_chain_id = (
            chain_id if chain_id is not None else self._deterministic_chain_id
        )
        resolved_nonce = nonce if nonce is not None else self._deterministic_nonce

        transaction = self._client.build_anchor_transaction(
            contract_address=self.contract_address,
            merkle_root=normalized_root,
            chain_id=resolved_chain_id,
            nonce=resolved_nonce,
            gas=gas,
            gas_price=gas_price,
            value=0,
            sender=sender,
        )
        signed = self._client.sign_transaction(transaction, self.private_key)
        if deterministic_mode:
            submitted_tx_hash = _normalize_hex(signed.tx_hash)
            receipt: Mapping[str, Any] = {
                "transaction_hash": submitted_tx_hash,
                "status": "signed_only",
                "block_number": 0,
            }
        else:
            submitted_tx_hash = _normalize_hex(self._client.submit_raw_transaction(signed.raw_transaction))
            receipt = self._client.get_transaction_receipt(submitted_tx_hash)

        receipt_tx_hash = _normalize_hex(
            receipt.get("transaction_hash", receipt.get("transactionHash", submitted_tx_hash))
        )
        receipt_status = str(receipt.get("status", "unknown")).lower()
        receipt_block_number = _to_int(receipt.get("block_number", receipt.get("blockNumber", 0)))
        receipt_id = str(receipt.get("receipt_id", "")).strip() or _deterministic_receipt_id(
            receipt_tx_hash,
            receipt_status,
            receipt_block_number,
        )

        metadata = SphereChainAnchorMetadata(
            endpoint=self.endpoint,
            contract_address=self.contract_address,
            sender=sender,
            chain_id=resolved_chain_id,
            nonce=resolved_nonce,
            gas=gas,
            gas_price=gas_price,
            value=0,
            signed_tx_hash=_normalize_hex(signed.tx_hash),
            receipt_status=receipt_status,
            receipt_block_number=receipt_block_number,
            deterministic_mode=deterministic_mode,
        )
        return SphereChainAnchorResult(
            merkle_root=normalized_root,
            receipt_id=receipt_id,
            tx_hash=receipt_tx_hash,
            metadata=metadata,
        )
