from __future__ import annotations

from typing import Any, Mapping

import pytest

from solis.execution.adapters.alpaca import AlpacaCredentials, AlpacaExecutionAdapter


class _FakeTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def send(
        self,
        *,
        workload_type: str,
        method: str,
        url: str,
        headers: Mapping[str, Any] | None = None,
        body: str | bytes | None = None,
        actor: str = "transport-client",
        policy_version: str = "v1",
        timeout_seconds: float = 10.0,
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        self.calls.append(
            {
                "workload_type": workload_type,
                "method": method,
                "url": url,
                "headers": dict(headers or {}),
                "body": body,
                "actor": actor,
                "policy_version": policy_version,
                "timeout_seconds": timeout_seconds,
                "metadata": dict(metadata or {}),
            }
        )
        return {
            "response": {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "body_text": '{"is_open": true, "timestamp": "2026-01-01T00:00:00Z"}',
                "elapsed_ms": 14.0,
                "mode": "direct",
                "adapter": "direct",
                "exit_fingerprint": "",
                "error": "",
                "ok": True,
            }
        }


class _DenyTransport:
    def send(self, **_: Any) -> Mapping[str, Any]:
        raise PermissionError("transport mode 'tor' is not allowed for workload 'market_execution'")


def test_alpaca_adapter_can_route_via_governed_transport() -> None:
    transport = _FakeTransport()
    adapter = AlpacaExecutionAdapter(
        credentials=AlpacaCredentials(api_key_id="k", api_secret_key="s"),
        transport_client=transport,
        base_url="https://paper-api.alpaca.markets",
    )

    clock = adapter.get_clock()
    assert clock["is_open"] is True

    assert transport.calls
    first = transport.calls[0]
    assert first["workload_type"] == "market_execution"
    assert first["method"] == "GET"
    assert first["url"].endswith("/v2/clock")


def test_alpaca_adapter_preserves_transport_policy_denials() -> None:
    adapter = AlpacaExecutionAdapter(
        credentials=AlpacaCredentials(api_key_id="k", api_secret_key="s"),
        transport_client=_DenyTransport(),
    )

    with pytest.raises(PermissionError):
        adapter.get_account()
