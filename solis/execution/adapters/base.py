from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable


@runtime_checkable
class ExecutionAdapter(Protocol):
    def get_account(self) -> dict[str, Any]: ...

    def get_clock(self) -> dict[str, Any]: ...

    def list_positions(self) -> dict[str, Any]: ...

    def list_orders(
        self,
        *,
        status: str = "open",
        limit: int = 200,
        symbols: Sequence[str] | None = None,
    ) -> dict[str, Any]: ...

    def get_order(self, *, order_id: str) -> dict[str, Any]: ...

    def cancel_order(self, *, order_id: str) -> dict[str, Any]: ...

    def cancel_all_orders(self) -> dict[str, Any]: ...

    def get_asset(self, *, symbol: str) -> dict[str, Any]: ...

    def submit_market_order(
        self,
        *,
        symbol: str,
        side: str,
        notional: float | str,
        time_in_force: str = "day",
        client_order_id: str | None = None,
    ) -> dict[str, Any]: ...

    def drain_events(self) -> list[dict[str, Any]]: ...
