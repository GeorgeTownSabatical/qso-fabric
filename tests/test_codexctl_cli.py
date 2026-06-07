from __future__ import annotations

from pathlib import Path

import pytest

from tools.codexctl import _build_parser, run


def test_codexctl_help_lists_transport() -> None:
    parser = _build_parser()
    help_text = parser.format_help()
    assert "transport" in help_text


def test_codexctl_transport_delegates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QSO_TRANSPORT_STATE_PATH", str(tmp_path / "transport_state.json"))
    monkeypatch.setenv("QSO_NETWORK_AUDIT_PATH", str(tmp_path / "network_audit.jsonl"))

    assert run(["transport", "set", "vpn", "--actor", "cli"]) == 0
    assert run(["transport", "status"]) == 0
