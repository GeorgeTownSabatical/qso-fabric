from __future__ import annotations

import pytest

from tools import dev_automation


def test_run_quick_orders_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(dev_automation, "_ensure_venv", lambda: calls.append("ensure"))
    monkeypatch.setattr(dev_automation, "_lint", lambda: calls.append("lint"))
    monkeypatch.setattr(dev_automation, "_tests", lambda: calls.append("tests"))

    dev_automation.run("quick")

    assert calls == ["ensure", "lint", "tests"]


def test_run_all_orders_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(dev_automation, "_ensure_venv", lambda: calls.append("ensure"))
    monkeypatch.setattr(dev_automation, "_lint", lambda: calls.append("lint"))
    monkeypatch.setattr(dev_automation, "_tests", lambda: calls.append("tests"))
    monkeypatch.setattr(dev_automation, "_smoke", lambda: calls.append("smoke"))

    dev_automation.run("all")

    assert calls == ["ensure", "lint", "tests", "smoke"]


def test_unknown_command_raises() -> None:
    with pytest.raises(SystemExit):
        dev_automation.run("unknown")


def test_run_submission_orders_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(dev_automation, "_ensure_venv", lambda: calls.append("ensure"))
    monkeypatch.setattr(dev_automation, "_submission", lambda: calls.append("submission"))

    dev_automation.run("submission")

    assert calls == ["ensure", "submission"]


def test_run_property_fraud_orders_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(dev_automation, "_ensure_venv", lambda: calls.append("ensure"))
    monkeypatch.setattr(dev_automation, "_property_fraud", lambda: calls.append("property_fraud"))

    dev_automation.run("property-fraud")

    assert calls == ["ensure", "property_fraud"]


def test_run_apn_db_orders_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(dev_automation, "_ensure_venv", lambda: calls.append("ensure"))
    monkeypatch.setattr(dev_automation, "_orange_county_apn_db", lambda: calls.append("apn_db"))

    dev_automation.run("apn-db")

    assert calls == ["ensure", "apn_db"]


def test_run_apn_scope_orders_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(dev_automation, "_ensure_venv", lambda: calls.append("ensure"))
    monkeypatch.setattr(dev_automation, "_orange_county_scope", lambda: calls.append("apn_scope"))

    dev_automation.run("apn-scope")

    assert calls == ["ensure", "apn_scope"]
