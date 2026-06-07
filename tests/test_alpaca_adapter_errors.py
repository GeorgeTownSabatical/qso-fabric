from __future__ import annotations

import io
from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

from solis.execution import (
    AlpacaAuthError,
    AlpacaCredentials,
    AlpacaExecutionAdapter,
    AlpacaHTTPError,
    AlpacaNetworkError,
    AlpacaRateLimitError,
    AlpacaValidationError,
)


def _adapter() -> AlpacaExecutionAdapter:
    return AlpacaExecutionAdapter(
        credentials=AlpacaCredentials(api_key_id="key", api_secret_key="secret"),
        base_url="https://paper-api.alpaca.markets",
    )


@pytest.mark.parametrize(
    ("status_code", "exc_type"),
    [
        (401, AlpacaAuthError),
        (403, AlpacaAuthError),
        (429, AlpacaRateLimitError),
        (400, AlpacaValidationError),
        (422, AlpacaValidationError),
        (500, AlpacaHTTPError),
    ],
)
def test_alpaca_http_error_taxonomy(monkeypatch: pytest.MonkeyPatch, status_code: int, exc_type: type[Exception]) -> None:
    payload = b'{"message":"simulated failure"}'

    def fake_urlopen(request: object, timeout: float = 0.0) -> object:
        _ = (request, timeout)
        raise HTTPError(
            url="https://paper-api.alpaca.markets/v2/account",
            code=status_code,
            msg="simulated",
            hdrs=Message(),
            fp=io.BytesIO(payload),
        )

    monkeypatch.setattr("solis.execution.adapters.alpaca.urlopen", fake_urlopen)

    adapter = _adapter()
    with pytest.raises(exc_type) as exc:
        adapter.get_account()

    as_dict = exc.value.as_dict()  # type: ignore[attr-defined]
    assert as_dict["status_code"] == status_code
    assert as_dict["operation"] == "get_account"
    assert as_dict["path"] == "/v2/account"

    events = adapter.drain_events()
    assert len(events) == 1
    assert events[0]["status_code"] == status_code


def test_alpaca_network_error_taxonomy(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: object, timeout: float = 0.0) -> object:
        _ = (request, timeout)
        raise URLError("network down")

    monkeypatch.setattr("solis.execution.adapters.alpaca.urlopen", fake_urlopen)

    adapter = _adapter()
    with pytest.raises(AlpacaNetworkError) as exc:
        adapter.get_clock()

    as_dict = exc.value.as_dict()
    assert as_dict["status_code"] is None
    assert as_dict["operation"] == "get_clock"
    assert as_dict["path"] == "/v2/clock"

    events = adapter.drain_events()
    assert len(events) == 1
    assert events[0]["status_code"] == 0
