from __future__ import annotations

import os
from pathlib import Path

import pytest

from solis.execution.adapters.alpaca import (
    AlpacaCredentials,
    AlpacaExecutionAdapter,
    build_replay_artifact,
    load_replay_artifact,
    verify_replay_artifact,
    write_replay_artifact,
)


def _alpaca_credentials() -> AlpacaCredentials:
    api_key = os.getenv("APCA_API_KEY_ID", "").strip()
    api_secret = os.getenv("APCA_API_SECRET_KEY", "").strip()
    if not api_key or not api_secret:
        pytest.skip("set APCA_API_KEY_ID and APCA_API_SECRET_KEY to run Alpaca live integration coverage")
    return AlpacaCredentials(api_key_id=api_key, api_secret_key=api_secret)


def _alpaca_base_url() -> str:
    return os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets").strip().rstrip("/")


@pytest.mark.live_alpaca
def test_alpaca_live_probe_builds_deterministic_replay_artifact(tmp_path: Path) -> None:
    credentials = _alpaca_credentials()
    base_url = _alpaca_base_url()
    adapter = AlpacaExecutionAdapter(credentials=credentials, base_url=base_url, timeout_seconds=8.0)

    account = adapter.get_account()
    clock = adapter.get_clock()
    events = adapter.drain_events()

    assert str(account.get("id", "")).strip()
    assert str(clock.get("timestamp", "")).strip()
    assert len(events) == 2

    artifact = build_replay_artifact(
        events,
        base_url=base_url,
        scenario="account_clock_probe",
    )
    artifact_path = tmp_path / "alpaca_account_clock_replay.json"
    write_replay_artifact(artifact_path, artifact)
    loaded_artifact = load_replay_artifact(artifact_path)

    assert loaded_artifact == artifact
    assert verify_replay_artifact(artifact)
    assert verify_replay_artifact(loaded_artifact)

    rebuilt_artifact = build_replay_artifact(
        events,
        base_url=base_url,
        scenario="account_clock_probe",
    )
    assert rebuilt_artifact["root_hash"] == artifact["root_hash"]
    assert rebuilt_artifact["artifact_hash"] == artifact["artifact_hash"]


@pytest.mark.live_alpaca
def test_alpaca_live_order_route_opt_in_with_replay_artifact(tmp_path: Path) -> None:
    if os.getenv("SOLIS_ALPACA_LIVE_ORDER") != "1":
        pytest.skip("set SOLIS_ALPACA_LIVE_ORDER=1 to opt in to live Alpaca order routing test")

    credentials = _alpaca_credentials()
    base_url = _alpaca_base_url()
    allow_live = os.getenv("SOLIS_ALPACA_ALLOW_LIVE") == "1"
    if "paper-api.alpaca.markets" not in base_url and not allow_live:
        pytest.skip("non-paper Alpaca URL requires SOLIS_ALPACA_ALLOW_LIVE=1")

    symbol = os.getenv("SOLIS_ALPACA_TEST_SYMBOL", "SPY").strip().upper()
    notional = float(os.getenv("SOLIS_ALPACA_TEST_NOTIONAL", "1.00"))

    adapter = AlpacaExecutionAdapter(credentials=credentials, base_url=base_url, timeout_seconds=8.0)
    account = adapter.get_account()

    buying_power_raw = str(account.get("buying_power", "0")).strip() or "0"
    try:
        buying_power = float(buying_power_raw)
    except ValueError:
        buying_power = 0.0
    if buying_power < notional:
        pytest.skip("Alpaca account buying_power is below configured SOLIS_ALPACA_TEST_NOTIONAL")

    order = adapter.submit_market_order(symbol=symbol, side="buy", notional=notional, time_in_force="day")
    events = adapter.drain_events()

    assert str(order.get("id", "")).strip()
    assert str(order.get("symbol", "")).upper() == symbol
    assert str(order.get("side", "")).lower() == "buy"
    assert len(events) >= 2

    artifact = build_replay_artifact(
        events,
        base_url=base_url,
        scenario="live_order_submission",
    )
    artifact_path = tmp_path / "alpaca_live_order_replay.json"
    write_replay_artifact(artifact_path, artifact)
    loaded_artifact = load_replay_artifact(artifact_path)

    assert verify_replay_artifact(artifact)
    assert verify_replay_artifact(loaded_artifact)
