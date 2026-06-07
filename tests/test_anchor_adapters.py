from __future__ import annotations

import hashlib
from typing import Any, Mapping

import pytest

from solis.anchor.eth_anchor import EthereumAnchor, SignedTransaction
from solis.anchor.spherechain_anchor import SphereChainAnchor, SphereChainSignedTransaction


class FakeEthereumClient:
    def __init__(self) -> None:
        self.chain_id_calls = 0
        self.nonce_calls: list[str] = []
        self.build_calls: list[dict[str, Any]] = []
        self.signed_transactions: list[Mapping[str, Any]] = []
        self.submitted_raw: list[bytes] = []

    def derive_address(self, private_key: str) -> str:
        return "0xfeedfacefeedfacefeedfacefeedfacefeedface"

    def get_chain_id(self) -> int:
        self.chain_id_calls += 1
        return 111

    def get_nonce(self, address: str) -> int:
        self.nonce_calls.append(address)
        return 9

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
        call = {
            "merkle_root": merkle_root,
            "chain_id": chain_id,
            "nonce": nonce,
            "gas": gas,
            "gas_price": gas_price,
            "value": value,
            "sender": sender,
        }
        self.build_calls.append(call)
        return {
            "to": "0xabc",
            "data": "0xdeadbeef",
            "chainId": chain_id,
            "nonce": nonce,
            "gas": gas,
            "gasPrice": gas_price,
            "value": value,
            "from": sender,
        }

    def sign_transaction(self, transaction: Mapping[str, Any], private_key: str) -> SignedTransaction:
        self.signed_transactions.append(transaction)
        return SignedTransaction(raw_transaction=b"\x01\x02", tx_hash="0xsigned")

    def submit_raw_transaction(self, raw_transaction: bytes) -> str:
        self.submitted_raw.append(raw_transaction)
        return "0xsubmitted"


class FakeSphereChainClient:
    def __init__(self) -> None:
        self.build_calls: list[dict[str, Any]] = []
        self.signed_transactions: list[Mapping[str, Any]] = []
        self.submitted_raw: list[bytes] = []
        self.receipt_calls: list[str] = []

    def derive_address(self, private_key: str) -> str:
        return "0x1111111111111111111111111111111111111111"

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
        call = {
            "contract_address": contract_address,
            "merkle_root": merkle_root,
            "chain_id": chain_id,
            "nonce": nonce,
            "gas": gas,
            "gas_price": gas_price,
            "value": value,
            "sender": sender,
        }
        self.build_calls.append(call)
        return {
            "contract": contract_address,
            "params": {"root": merkle_root},
            "chain_id": chain_id,
            "nonce": nonce,
            "gas": gas,
            "gas_price": gas_price,
            "value": value,
            "from": sender,
        }

    def sign_transaction(self, transaction: Mapping[str, Any], private_key: str) -> SphereChainSignedTransaction:
        self.signed_transactions.append(transaction)
        return SphereChainSignedTransaction(raw_transaction=b"raw-sphere", tx_hash="0xabc123")

    def submit_raw_transaction(self, raw_transaction: bytes) -> str:
        self.submitted_raw.append(raw_transaction)
        return "0xdef456"

    def get_transaction_receipt(self, tx_hash: str) -> Mapping[str, Any]:
        self.receipt_calls.append(tx_hash)
        return {
            "transactionHash": tx_hash,
            "status": "committed",
            "blockNumber": "42",
        }


def test_ethereum_anchor_builds_signs_and_submits_raw_tx() -> None:
    client = FakeEthereumClient()
    adapter = EthereumAnchor(
        rpc_url="http://example.invalid",
        contract_address="0xcontract",
        private_key="0xprivate",
        client=client,
    )

    result = adapter.anchor(
        "0X" + "AA" * 32,
        chain_id=5,
        nonce=7,
        gas=55_000,
        gas_price=77,
    )

    assert len(client.build_calls) == 1
    build = client.build_calls[0]
    assert build["merkle_root"] == bytes.fromhex("aa" * 32)
    assert build["chain_id"] == 5
    assert build["nonce"] == 7
    assert build["gas"] == 55_000
    assert build["gas_price"] == 77
    assert build["value"] == 0
    assert build["sender"] == "0xfeedfacefeedfacefeedfacefeedfacefeedface"
    assert client.submitted_raw == [b"\x01\x02"]

    assert result.merkle_root == "0x" + "aa" * 32
    assert result.chain_id == 5
    assert result.tx_hash == "0xsubmitted"
    assert result.metadata.chain_id == 5
    assert result.metadata.nonce == 7
    assert result.metadata.gas == 55_000
    assert result.metadata.gas_price == 77
    assert result.metadata.value == 0
    assert result.metadata.data == "0xdeadbeef"
    assert result.metadata.signed_tx_hash == "0xsigned"
    assert result.metadata.deterministic_mode is False
    assert client.chain_id_calls == 0
    assert client.nonce_calls == []


def test_ethereum_anchor_deterministic_mode_uses_signed_hash_without_submit() -> None:
    client = FakeEthereumClient()
    adapter = EthereumAnchor(
        rpc_url="http://example.invalid",
        contract_address="0xcontract",
        private_key="0xprivate",
        client=client,
        deterministic_chain_id=99,
        deterministic_nonce=4,
    )

    result = adapter.anchor("0x" + "bb" * 32, deterministic_mode=True)

    assert result.chain_id == 99
    assert result.tx_hash == "0xsigned"
    assert result.metadata.nonce == 4
    assert result.metadata.deterministic_mode is True
    assert client.submitted_raw == []
    assert client.chain_id_calls == 0
    assert client.nonce_calls == []


def test_spherechain_anchor_builds_signs_submits_and_parses_receipt_deterministically() -> None:
    client = FakeSphereChainClient()
    adapter = SphereChainAnchor(
        endpoint="https://spherechain.invalid",
        private_key="sphere-private",
        contract_address="sphere-contract",
        client=client,
    )

    result = adapter.anchor(
        "0x" + "cc" * 32,
        chain_id=314,
        nonce=12,
        gas=66_000,
        gas_price=101,
    )

    assert len(client.build_calls) == 1
    build = client.build_calls[0]
    assert build["contract_address"] == "sphere-contract"
    assert build["merkle_root"] == "0x" + "cc" * 32
    assert build["chain_id"] == 314
    assert build["nonce"] == 12
    assert build["gas"] == 66_000
    assert build["gas_price"] == 101
    assert build["value"] == 0
    assert client.submitted_raw == [b"raw-sphere"]
    assert client.receipt_calls == ["0xdef456"]

    expected_receipt_id = hashlib.sha256("0xdef456:committed:42".encode("utf-8")).hexdigest()
    assert result.merkle_root == "0x" + "cc" * 32
    assert result.tx_hash == "0xdef456"
    assert result.receipt_id == expected_receipt_id
    assert result.metadata.chain_id == 314
    assert result.metadata.nonce == 12
    assert result.metadata.gas == 66_000
    assert result.metadata.gas_price == 101
    assert result.metadata.receipt_status == "committed"
    assert result.metadata.receipt_block_number == 42
    assert result.metadata.signed_tx_hash == "0xabc123"
    assert result.metadata.deterministic_mode is False


def test_spherechain_anchor_deterministic_mode_skips_network_submission() -> None:
    client = FakeSphereChainClient()
    adapter = SphereChainAnchor(
        endpoint="https://spherechain.invalid",
        private_key="sphere-private",
        contract_address="sphere-contract",
        client=client,
        deterministic_chain_id=77,
        deterministic_nonce=2,
    )

    result = adapter.anchor("0x" + "dd" * 32, deterministic_mode=True)

    expected_receipt_id = hashlib.sha256("0xabc123:signed_only:0".encode("utf-8")).hexdigest()
    assert result.tx_hash == "0xabc123"
    assert result.receipt_id == expected_receipt_id
    assert result.metadata.chain_id == 77
    assert result.metadata.nonce == 2
    assert result.metadata.receipt_status == "signed_only"
    assert result.metadata.receipt_block_number == 0
    assert result.metadata.deterministic_mode is True
    assert client.submitted_raw == []
    assert client.receipt_calls == []


@pytest.mark.parametrize("root", ["xyz", "0x1234"])
def test_anchor_adapters_validate_merkle_root(root: str) -> None:
    with pytest.raises(ValueError):
        EthereumAnchor(
            rpc_url="http://example.invalid",
            contract_address="0xcontract",
            private_key="0xprivate",
            client=FakeEthereumClient(),
        ).anchor(root, chain_id=1, nonce=0)

    with pytest.raises(ValueError):
        SphereChainAnchor(
            endpoint="https://spherechain.invalid",
            private_key="sphere-private",
            contract_address="sphere-contract",
            client=FakeSphereChainClient(),
        ).anchor(root)
