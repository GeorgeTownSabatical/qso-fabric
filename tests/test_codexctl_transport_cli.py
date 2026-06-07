from __future__ import annotations

from pathlib import Path

import pytest

from tools.codexctl_transport import _build_parser, run


def test_codexctl_transport_help_lists_commands() -> None:
    parser = _build_parser()
    help_text = parser.format_help()
    for command in ("set", "status", "health", "policy"):
        assert command in help_text


def test_codexctl_transport_set_and_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QSO_TRANSPORT_STATE_PATH", str(tmp_path / "transport_state.json"))
    monkeypatch.setenv("QSO_NETWORK_AUDIT_PATH", str(tmp_path / "network_audit.jsonl"))

    assert run(["set", "tor", "--actor", "cli"]) == 0
    assert run(["status"]) == 0
    assert run(["health"]) == 0
    assert run(["policy"]) == 0
