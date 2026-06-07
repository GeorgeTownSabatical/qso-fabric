from __future__ import annotations

from solis.execution import AlpacaCredentials, AlpacaExecutionAdapter, ExecutionAdapter


def test_alpaca_adapter_conforms_to_execution_adapter_protocol() -> None:
    adapter = AlpacaExecutionAdapter(
        credentials=AlpacaCredentials(api_key_id="key", api_secret_key="secret"),
        base_url="https://paper-api.alpaca.markets",
    )
    assert isinstance(adapter, ExecutionAdapter)


def test_execution_adapter_surface_methods_are_exposed() -> None:
    adapter = AlpacaExecutionAdapter(
        credentials=AlpacaCredentials(api_key_id="key", api_secret_key="secret"),
        base_url="https://paper-api.alpaca.markets",
    )
    for method in (
        "get_account",
        "get_clock",
        "list_positions",
        "list_orders",
        "get_order",
        "cancel_order",
        "cancel_all_orders",
        "get_asset",
        "submit_market_order",
        "drain_events",
    ):
        assert hasattr(adapter, method), f"missing execution adapter method: {method}"
