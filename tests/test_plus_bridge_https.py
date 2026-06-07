from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone

import pytest

from tools.qso_plus_bridge_http import PerIPRateLimiter, _build_tls_context


def test_build_tls_context_none_when_not_configured() -> None:
    assert _build_tls_context(None, None) is None


def test_build_tls_context_requires_both_paths() -> None:
    with pytest.raises(ValueError):
        _build_tls_context("cert.pem", None)
    with pytest.raises(ValueError):
        _build_tls_context(None, "key.pem")


def test_per_ip_rate_limiter_enforces_budget() -> None:
    limiter = PerIPRateLimiter(2)
    assert limiter.allow("127.0.0.1")
    assert limiter.allow("127.0.0.1")
    assert not limiter.allow("127.0.0.1")

    # Simulate time window expiry by manually shifting timestamps.
    limiter._by_ip["127.0.0.1"] = deque(  # type: ignore[attr-defined]
        [
            datetime.now(timezone.utc) - timedelta(minutes=2),
            datetime.now(timezone.utc) - timedelta(minutes=2),
        ]
    )
    assert limiter.allow("127.0.0.1")
