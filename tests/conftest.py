from __future__ import annotations

import os
import sys

import pytest


def pytest_sessionstart(session: pytest.Session) -> None:
    print(f"[pytest] executable={sys.executable}")


@pytest.fixture(autouse=True, scope="session")
def _configure_test_env() -> None:
    prior_env = os.environ.get("QSO_ENV")
    prior_secret = os.environ.get("QSO_FABRIC_SECRET")
    os.environ["QSO_ENV"] = "test"
    os.environ["QSO_FABRIC_SECRET"] = "qso-fabric-test-secret"
    try:
        yield
    finally:
        if prior_env is None:
            os.environ.pop("QSO_ENV", None)
        else:
            os.environ["QSO_ENV"] = prior_env
        if prior_secret is None:
            os.environ.pop("QSO_FABRIC_SECRET", None)
        else:
            os.environ["QSO_FABRIC_SECRET"] = prior_secret
