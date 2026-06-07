from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

try:
    from web3 import Web3
except Exception:  # pragma: no cover - optional dependency
    Web3 = None  # type: ignore[assignment]

_ANCHOR_FUNCTION_ABI: list[dict[str, Any]] = [
    {
        "inputs": [{"internalType": "bytes32", "name": "root", "type": "bytes32"}],
        "name": "anchorRoot",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


@dataclass(frozen=True)
class SignedTransaction:
    raw_transaction: bytes
    tx_hash: str


class EthereumAnchorClient(Protocol):
    def derive_address(self, private_key: str) -> str:
        ...

    def get_chain_id(self) -> int:
        ...

    def get_nonce(self, address: str) -> int:
        ...

    def build_anchor_transaction(
        self,
        *,
        merkle_root: bytes,
        chain_id: int,
        nonce: int,
        gas: int,
        gas_price: int,
        value: int,
        sender: str,
    ) -> dict[str, Any]:
        ...

    def sign_transaction(self, transaction: Mapping[str, Any], private_key: str) -> SignedTransaction:
        ...

    def submit_raw_transaction(self, raw_transaction: bytes) -> str:
        ...


@dataclass(frozen=True)
class EthereumAnchorMetadata:
    contract_address: str
    sender: str
    chain_id: int
    nonce: int
    gas: int
    gas_price: int
    value: int
    data: str
    signed_tx_hash: str
    deterministic_mode: bool


@dataclass
class EthereumAnchorResult:
    merkle_root: str
    tx_hash: str
    chain_id: int
    metadata: EthereumAnchorMetadata


class Web3EthereumAnchorClient:
    def __init__(self, rpc_url: str, contract_address: str) -> None:
        if Web3 is None:  # pragma: no cover - guarded in constructor path
            raise RuntimeError("web3 is required for Ethereum anchoring")
        self._w3 = Web3(Web3.HTTPProvider(rpc_url))
        checksum_address = self._w3.to_checksum_address(contract_address)
        self._contract = self._w3.eth.contract(address=checksum_address, abi=_ANCHOR_FUNCTION_ABI)

    def derive_address(self, private_key: str) -> str:
        return str(self._w3.eth.account.from_key(private_key).address)

    def get_chain_id(self) -> int:
        return int(self._w3.eth.chain_id)

    def get_nonce(self, address: str) -> int:
        return int(self._w3.eth.get_transaction_count(address))

    def build_anchor_transaction(
        self,
        *,
        merkle_root: bytes,
        chain_id: int,
        nonce: int,
        gas: int,
        gas_price: int,
        value: int,
        sender: str,
    ) -> dict[str, Any]:
        return dict(
            self._contract.functions.anchorRoot(merkle_root).build_transaction(
                {
                    "chainId": chain_id,
                    "nonce": nonce,
                    "gas": gas,
                    "gasPrice": gas_price,
                    "value": value,
                    "from": sender,
                }
            )
        )

    def sign_transaction(self, transaction: Mapping[str, Any], private_key: str) -> SignedTransaction:
        signed = self._w3.eth.account.sign_transaction(dict(transaction), private_key)
        raw_candidate = getattr(signed, "raw_transaction", None)
        if raw_candidate is None:  # pragma: no cover - compatibility fallback
            raw_candidate = getattr(signed, "rawTransaction")
        raw_transaction = bytes(raw_candidate)
        tx_hash = _normalize_hex(getattr(signed, "hash", self._w3.keccak(raw_transaction)))
        return SignedTransaction(raw_transaction=raw_transaction, tx_hash=tx_hash)

    def submit_raw_transaction(self, raw_transaction: bytes) -> str:
        sent = self._w3.eth.send_raw_transaction(raw_transaction)
        return _normalize_hex(sent)


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


class EthereumAnchor:
    def __init__(
        self,
        rpc_url: str,
        contract_address: str,
        private_key: str,
        *,
        client: EthereumAnchorClient | None = None,
        deterministic_chain_id: int = 1,
        deterministic_nonce: int = 0,
    ) -> None:
        if client is None:
            if Web3 is None:
                raise RuntimeError("web3 is required for Ethereum anchoring")
            client = Web3EthereumAnchorClient(rpc_url=rpc_url, contract_address=contract_address)

        self._client = client
        self.contract_address = contract_address
        self.private_key = private_key
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
    ) -> EthereumAnchorResult:
        normalized_root = _normalize_merkle_root(merkle_root)
        merkle_root_bytes = bytes.fromhex(normalized_root[2:])
        sender = self._client.derive_address(self.private_key)
        resolved_chain_id = (
            chain_id
            if chain_id is not None
            else (self._deterministic_chain_id if deterministic_mode else self._client.get_chain_id())
        )
        resolved_nonce = (
            nonce
            if nonce is not None
            else (self._deterministic_nonce if deterministic_mode else self._client.get_nonce(sender))
        )

        transaction = self._client.build_anchor_transaction(
            merkle_root=merkle_root_bytes,
            chain_id=resolved_chain_id,
            nonce=resolved_nonce,
            gas=gas,
            gas_price=gas_price,
            value=0,
            sender=sender,
        )
        signed = self._client.sign_transaction(transaction, self.private_key)
        tx_hash = signed.tx_hash if deterministic_mode else self._client.submit_raw_transaction(signed.raw_transaction)

        data_field = transaction.get("data", "0x")
        metadata = EthereumAnchorMetadata(
            contract_address=self.contract_address,
            sender=sender,
            chain_id=resolved_chain_id,
            nonce=resolved_nonce,
            gas=gas,
            gas_price=gas_price,
            value=0,
            data=_normalize_hex(data_field),
            signed_tx_hash=_normalize_hex(signed.tx_hash),
            deterministic_mode=deterministic_mode,
        )
        return EthereumAnchorResult(
            merkle_root=normalized_root,
            tx_hash=_normalize_hex(tx_hash),
            chain_id=resolved_chain_id,
            metadata=metadata,
        )
