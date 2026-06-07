from __future__ import annotations

import json
from typing import Literal
from urllib.parse import parse_qs, urlparse

import pytest

from solis.execution import AlpacaCredentials, AlpacaExecutionAdapter


class _FakeResponse:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self._payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> Literal[False]:
        _ = (exc_type, exc, tb)
        return False


def test_alpaca_adapter_execution_surface_and_deterministic_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[tuple[str, str, dict[str, str]]] = []

    def fake_urlopen(request: object, timeout: float = 0.0) -> _FakeResponse:
        _ = timeout
        method = str(request.get_method())  # type: ignore[attr-defined]
        url = str(request.full_url)  # type: ignore[attr-defined]
        parsed = urlparse(url)
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        requests.append((method, parsed.path, query))

        if method == "GET" and parsed.path == "/v2/account":
            return _FakeResponse(200, {"status": "ACTIVE", "id": "acct-1"})
        if method == "GET" and parsed.path == "/v2/clock":
            return _FakeResponse(200, {"is_open": True, "timestamp": "2026-02-25T14:30:00Z"})
        if method == "GET" and parsed.path == "/v2/positions":
            return _FakeResponse(200, [{"symbol": "MSFT", "qty": "2"}, {"symbol": "AAPL", "qty": "1"}])
        if method == "GET" and parsed.path == "/v2/orders":
            return _FakeResponse(200, [{"id": "ord-2"}, {"id": "ord-1"}])
        if method == "GET" and parsed.path == "/v2/orders/ord-1":
            return _FakeResponse(200, {"id": "ord-1", "status": "new"})
        if method == "DELETE" and parsed.path == "/v2/orders/ord-1":
            return _FakeResponse(200, {"id": "ord-1", "status": "canceled"})
        if method == "DELETE" and parsed.path == "/v2/orders":
            return _FakeResponse(200, [{"id": "ord-2"}, {"id": "ord-1"}])
        if method == "GET" and parsed.path == "/v2/assets/AAPL":
            return _FakeResponse(200, {"symbol": "AAPL", "tradable": True})
        if method == "POST" and parsed.path == "/v2/orders":
            return _FakeResponse(200, {"id": "ord-3", "status": "accepted"})
        raise AssertionError(f"unexpected request {method} {parsed.path}?{parsed.query}")

    monkeypatch.setattr("solis.execution.adapters.alpaca.urlopen", fake_urlopen)

    adapter = AlpacaExecutionAdapter(
        credentials=AlpacaCredentials(api_key_id="key", api_secret_key="secret"),
        base_url="https://paper-api.alpaca.markets",
    )

    account = adapter.get_account()
    clock = adapter.get_clock()
    positions = adapter.list_positions()
    orders = adapter.list_orders(status="all", limit=2, symbols=["msft", "aapl"])
    order = adapter.get_order(order_id="ord-1")
    canceled = adapter.cancel_order(order_id="ord-1")
    cancel_all = adapter.cancel_all_orders()
    asset = adapter.get_asset(symbol="aapl")
    submit = adapter.submit_market_order(symbol="aapl", side="buy", notional="10.00")

    assert account["id"] == "acct-1"
    assert clock["is_open"] is True
    assert [row["symbol"] for row in positions["positions"]] == ["AAPL", "MSFT"]
    assert [row["id"] for row in orders["orders"]] == ["ord-1", "ord-2"]
    assert order["id"] == "ord-1"
    assert canceled["status"] == "canceled"
    assert [row["id"] for row in cancel_all["cancellations"]] == ["ord-1", "ord-2"]
    assert asset["symbol"] == "AAPL"
    assert submit["status"] == "accepted"

    assert ("GET", "/v2/orders", {"status": "all", "limit": "2", "symbols": "AAPL,MSFT"}) in requests
    ops = [event["operation"] for event in adapter.drain_events()]
    assert ops == [
        "get_account",
        "get_clock",
        "list_positions",
        "list_orders",
        "get_order",
        "cancel_order",
        "cancel_all_orders",
        "get_asset",
        "submit_market_order",
    ]
