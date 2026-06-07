from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any, Iterator, Mapping
from urllib.request import Request, urlopen

import pytest

from solis.anchor.eth_anchor import EthereumAnchor
from solis.anchor.spherechain_anchor import SphereChainAnchor, SphereChainSignedTransaction

_ANVIL_DEFAULT_PRIVATE_KEY = (
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
)


@dataclass
class _SphereMockState:
    request_log: list[tuple[str, str, Mapping[str, Any] | None]] = field(default_factory=list)
    receipts: dict[str, dict[str, Any]] = field(default_factory=dict)


class _HttpSphereChainClient:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint.rstrip("/")

    def _post_json(self, path: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
        request = Request(
            f"{self.endpoint}{path}",
            data=encoded,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_json(self, path: str) -> Mapping[str, Any]:
        request = Request(f"{self.endpoint}{path}", method="GET")
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def derive_address(self, private_key: str) -> str:
        response = self._post_json("/derive-address", {"private_key": private_key})
        return str(response["address"])

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
        response = self._post_json(
            "/build-anchor-transaction",
            {
                "contract_address": contract_address,
                "merkle_root": merkle_root,
                "chain_id": chain_id,
                "nonce": nonce,
                "gas": gas,
                "gas_price": gas_price,
                "value": value,
                "sender": sender,
            },
        )
        return dict(response["transaction"])

    def sign_transaction(self, transaction: Mapping[str, Any], private_key: str) -> SphereChainSignedTransaction:
        response = self._post_json(
            "/sign-transaction",
            {
                "transaction": dict(transaction),
                "private_key": private_key,
            },
        )
        raw_transaction = bytes.fromhex(str(response["raw_transaction"]))
        return SphereChainSignedTransaction(raw_transaction=raw_transaction, tx_hash=str(response["tx_hash"]))

    def submit_raw_transaction(self, raw_transaction: bytes) -> str:
        response = self._post_json("/submit-raw-transaction", {"raw_transaction": raw_transaction.hex()})
        return str(response["tx_hash"])

    def get_transaction_receipt(self, tx_hash: str) -> Mapping[str, Any]:
        return self._get_json(f"/receipt/{tx_hash}")


def _build_spherechain_handler(state: _SphereMockState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - suppress noisy server logs
            return

        def _read_json(self) -> Mapping[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            data = self.rfile.read(length) if length else b"{}"
            return json.loads(data.decode("utf-8"))

        def _write_json(self, status: int, payload: Mapping[str, Any]) -> None:
            body = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            request_body = self._read_json()
            state.request_log.append(("POST", self.path, request_body))

            if self.path == "/derive-address":
                private_key = str(request_body["private_key"])
                digest = hashlib.sha256(f"addr:{private_key}".encode("utf-8")).hexdigest()[:40]
                self._write_json(200, {"address": "0x" + digest})
                return

            if self.path == "/build-anchor-transaction":
                transaction = {
                    "type": "anchorRoot",
                    "method": "anchorRoot",
                    "contract": str(request_body["contract_address"]),
                    "params": {"root": str(request_body["merkle_root"])},
                    "chain_id": int(request_body["chain_id"]),
                    "nonce": int(request_body["nonce"]),
                    "gas": int(request_body["gas"]),
                    "gas_price": int(request_body["gas_price"]),
                    "value": int(request_body["value"]),
                    "from": str(request_body["sender"]),
                    "endpoint": "local-spherechain",
                }
                self._write_json(200, {"transaction": transaction})
                return

            if self.path == "/sign-transaction":
                transaction = dict(request_body["transaction"])
                private_key = str(request_body["private_key"])
                canonical_tx = json.dumps(transaction, sort_keys=True, separators=(",", ":"))
                signature = hashlib.sha256(f"{private_key}:{canonical_tx}".encode("utf-8")).hexdigest()
                envelope = {"tx": transaction, "signature": signature}
                raw_transaction = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
                tx_hash = "0x" + hashlib.sha256(raw_transaction).hexdigest()
                self._write_json(
                    200,
                    {
                        "raw_transaction": raw_transaction.hex(),
                        "tx_hash": tx_hash,
                    },
                )
                return

            if self.path == "/submit-raw-transaction":
                raw_transaction = bytes.fromhex(str(request_body["raw_transaction"]))
                tx_hash = "0x" + hashlib.sha256(raw_transaction).hexdigest()
                state.receipts.setdefault(
                    tx_hash,
                    {
                        "transaction_hash": tx_hash,
                        "status": "committed",
                        "block_number": len(state.receipts) + 1,
                    },
                )
                self._write_json(200, {"tx_hash": tx_hash})
                return

            self._write_json(404, {"error": "unknown endpoint"})

        def do_GET(self) -> None:  # noqa: N802
            state.request_log.append(("GET", self.path, None))
            if self.path.startswith("/receipt/"):
                tx_hash = self.path.split("/receipt/", 1)[1]
                receipt = state.receipts.get(tx_hash)
                if receipt is None:
                    self._write_json(404, {"error": "receipt not found"})
                    return
                self._write_json(200, receipt)
                return

            self._write_json(404, {"error": "unknown endpoint"})

    return Handler


@contextmanager
def _spherechain_server(state: _SphereMockState) -> Iterator[str]:
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _build_spherechain_handler(state))
    except OSError as exc:
        pytest.skip(f"local SphereChain mock server unavailable: {exc}")

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _candidate_eth_rpc_urls() -> list[str]:
    candidates: list[str] = []
    env_rpc = os.getenv("SOLIS_ETH_RPC_URL", "").strip()
    if env_rpc:
        candidates.append(env_rpc)

    candidates.extend(
        [
            "http://127.0.0.1:8545",
            "http://localhost:8545",
            "http://127.0.0.1:8546",
            "http://localhost:8546",
        ]
    )

    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _candidate_eth_private_keys() -> list[str]:
    keys: list[str] = []
    env_private_key = os.getenv("SOLIS_ETH_PRIVATE_KEY", "").strip()
    if env_private_key:
        keys.append(env_private_key)
    keys.append(_ANVIL_DEFAULT_PRIVATE_KEY)

    deduped: list[str] = []
    for key in keys:
        if key and key not in deduped:
            deduped.append(key)
    return deduped


def test_ethereum_anchor_live_web3_tx_path_skips_without_local_dev_chain() -> None:
    try:
        from web3 import Web3
    except Exception as exc:
        pytest.skip(f"web3 not available: {exc}")

    chosen: tuple[Any, str] | None = None
    for rpc_url in _candidate_eth_rpc_urls():
        provider = Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 1.5})
        web3 = Web3(provider)
        try:
            if not web3.is_connected():
                continue
            _ = int(web3.eth.chain_id)
        except Exception:
            continue

        chosen = (web3, rpc_url)
        break

    if chosen is None:
        pytest.skip(
            "No local Ethereum dev RPC reachable. "
            "Start anvil/hardhat or set SOLIS_ETH_RPC_URL for live adapter integration coverage."
        )

    web3, rpc_url = chosen

    selected_key: str | None = None
    sender_address: str | None = None
    sender_balance = 0
    for private_key in _candidate_eth_private_keys():
        try:
            sender = web3.eth.account.from_key(private_key).address
            balance = int(web3.eth.get_balance(sender))
        except Exception:
            continue
        if balance > 0:
            selected_key = private_key
            sender_address = str(sender)
            sender_balance = balance
            break

    if selected_key is None or sender_address is None:
        pytest.skip(
            "No funded key found for the local dev chain. "
            "Set SOLIS_ETH_PRIVATE_KEY to a funded test account."
        )

    contract_address_raw = os.getenv("SOLIS_ETH_CONTRACT_ADDRESS", sender_address)
    try:
        contract_address = web3.to_checksum_address(contract_address_raw)
    except Exception:
        pytest.skip(f"SOLIS_ETH_CONTRACT_ADDRESS is invalid: {contract_address_raw}")

    try:
        gas_price = max(int(web3.eth.gas_price), 1)
    except Exception:
        gas_price = 1_000_000_000

    gas_limit = 180_000
    if sender_balance < gas_price * gas_limit:
        pytest.skip("Funded test account does not have enough balance for an anchor transaction")

    merkle_root = "0x" + hashlib.sha256(f"solis-live:{sender_address}".encode("utf-8")).hexdigest()
    adapter = EthereumAnchor(
        rpc_url=rpc_url,
        contract_address=contract_address,
        private_key=selected_key,
    )
    result = adapter.anchor(merkle_root, gas=gas_limit, gas_price=gas_price)

    receipt = web3.eth.wait_for_transaction_receipt(result.tx_hash, timeout=20)
    transaction = web3.eth.get_transaction(result.tx_hash)
    transaction_to = transaction.get("to")
    transaction_input = str(transaction.get("input", "0x"))

    assert result.merkle_root == merkle_root
    assert result.chain_id == int(web3.eth.chain_id)
    assert result.metadata.deterministic_mode is False
    assert result.metadata.sender.lower() == sender_address.lower()
    assert result.metadata.chain_id == int(web3.eth.chain_id)
    assert result.metadata.gas == gas_limit
    assert result.metadata.gas_price == gas_price
    assert transaction_to is not None
    assert str(transaction_to).lower() == contract_address.lower()
    assert transaction_input.lower() == result.metadata.data.lower()
    assert int(receipt["status"]) == 1


def test_spherechain_anchor_local_server_request_response_flow() -> None:
    state = _SphereMockState()
    with _spherechain_server(state) as endpoint:
        adapter = SphereChainAnchor(
            endpoint=endpoint,
            private_key="spherechain-live-key",
            contract_address="spherechain-live-anchor",
            client=_HttpSphereChainClient(endpoint),
        )

        merkle_root = "0x" + hashlib.sha256(b"solis-sphere-live").hexdigest()
        result = adapter.anchor(
            merkle_root,
            chain_id=2_026,
            nonce=3,
            gas=120_000,
            gas_price=9,
        )

    request_paths = [f"{method} {path}" for method, path, _ in state.request_log]
    assert request_paths == [
        "POST /derive-address",
        "POST /build-anchor-transaction",
        "POST /sign-transaction",
        "POST /submit-raw-transaction",
        f"GET /receipt/{result.tx_hash}",
    ]

    build_request = state.request_log[1][2]
    assert build_request is not None
    assert str(build_request["contract_address"]) == "spherechain-live-anchor"
    assert str(build_request["merkle_root"]) == merkle_root
    assert int(build_request["chain_id"]) == 2_026
    assert int(build_request["nonce"]) == 3

    assert result.merkle_root == merkle_root
    assert result.tx_hash.startswith("0x")
    assert len(result.tx_hash) == 66
    assert result.metadata.chain_id == 2_026
    assert result.metadata.nonce == 3
    assert result.metadata.receipt_status == "committed"
    assert result.metadata.receipt_block_number == 1
    assert result.metadata.deterministic_mode is False
