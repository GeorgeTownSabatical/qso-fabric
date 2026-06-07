from __future__ import annotations

from pathlib import Path

import pytest

from api.mcp_tools.qso_tools import QSOMCPTools
from services.transport.replay_engine import TransportReplayEngine


def _tools(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> QSOMCPTools:
    monkeypatch.setenv("QSO_TRANSPORT_STATE_PATH", str(tmp_path / "transport_state.json"))
    monkeypatch.setenv("QSO_NETWORK_AUDIT_PATH", str(tmp_path / "network_audit.jsonl"))
    monkeypatch.setenv("QSO_TRANSPORT_POLICY_VERSION", "v1")
    return QSOMCPTools()


def test_transport_set_mutates_qso_state_and_emits_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tools = _tools(monkeypatch, tmp_path)

    out = tools.qso_transport_set("vpn", actor="ops", policy_version="v1", node_id="node-a")

    assert out["state"]["mode"] == "vpn"
    timeline = tools.qso_timeline("qso://infra.transport")
    assert timeline
    assert timeline[-1]["delta"]["mode"] == "vpn"
    assert timeline[-1]["actor"] == "ops"


def test_transport_policy_gates_market_execution_on_tor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tools = _tools(monkeypatch, tmp_path)
    tools.qso_transport_set("tor", actor="research")

    ok = tools.qso_transport_send(
        workload_type="research",
        method="GET",
        url="mock://research.endpoint/ping",
        actor="research",
    )
    assert ok["response"]["ok"] is True
    assert ok["response"]["mode"] == "tor"

    with pytest.raises(PermissionError):
        tools.qso_transport_send(
            workload_type="market_execution",
            method="POST",
            url="mock://broker.execute/order",
            body='{"symbol":"SPY"}',
            actor="trader",
        )


def test_transport_audit_hash_chain_replay(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tools = _tools(monkeypatch, tmp_path)
    tools.qso_transport_set("direct", actor="ops")
    tools.qso_transport_send(workload_type="research", method="GET", url="mock://service.alpha/a", actor="ops")
    tools.qso_transport_send(workload_type="model_training", method="GET", url="mock://service.alpha/b", actor="ops")

    assert tools.runtime.transport.verify_audit_chain() is True

    audit_path = Path(tmp_path / "network_audit.jsonl")
    replay = TransportReplayEngine(audit_path).replay()
    assert replay.total_events >= 3
    assert replay.hash_chain_ok is True
    assert "direct" in replay.modes_seen


def test_transport_health_and_metrics_are_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tools = _tools(monkeypatch, tmp_path)
    tools.qso_transport_set("vpn", actor="ops")
    tools.qso_transport_send(workload_type="model_training", method="GET", url="mock://dataset.fetch/1", actor="ops")
    tools.qso_transport_send(workload_type="model_training", method="GET", url="mock://dataset.fetch/2", actor="ops")

    health = tools.qso_transport_health()
    assert health["vpn"]["samples"] >= 2
    assert health["vpn"]["health_status"] in {"healthy", "slow", "degraded"}

    metrics = tools.qso_transport_metrics()
    key = "model_training:vpn"
    assert key in metrics
    assert int(metrics[key]["samples"]) >= 2

    status = tools.qso_transport_status()
    assert status["mode"] == "vpn"
    assert "hardware_identity_hash" in status
