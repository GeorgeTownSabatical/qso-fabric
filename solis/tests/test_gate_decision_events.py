from __future__ import annotations

from typing import Any

import pytest

from solis.config import SolisConfig
from solis.integration.gates import GateResult
from solis.services.gate_audit import emit_gate_decision
from solis.services.solis_constellation_service import SolisConstellationService
from solis.services.solis_meta_signal_service import SolisMetaSignalService
from solis.services.solis_star_service import SolisStarService


def _gate_uris(qso: Any, prefix: str) -> list[str]:
    tools = getattr(qso, "tools", None)
    if tools is None:
        return []
    return sorted([uri for uri in tools.runtime.registry.list_uris() if uri.startswith(prefix)])


def _health_payload(qso: Any, scope: str) -> dict[str, Any]:
    return qso.read(f"qso://solis.gate.health.{scope}")["state_layer"]


def test_star_gate_decisions_emitted() -> None:
    config = SolisConfig(anchor_interval=2, runtime_gate_enabled=True)
    service = SolisStarService(config=config)
    service.create_star(star_id="gateaudit", chain_id="spherechain")
    service.patch_star(
        star_uri_or_id="gateaudit",
        delta={"mass": 0.2, "luminosity": 0.1, "entropy_index": 0.02, "magnetic_field": -0.01},
        actor="gate-audit",
    )

    uris = _gate_uris(service.qso, "qso://solis.gate.star.")
    assert uris
    payload = service.qso.read(uris[0])["state_layer"]
    assert payload["scope"] == "star"
    assert payload["stage"] in {"precommit", "postcommit"}
    assert payload["gate"] in {"gate1", "gate2", "gate3"}
    assert isinstance(payload["passed"], bool)

    health = _health_payload(service.qso, "star")
    assert health["scope"] == "star"
    assert health["decision_event_count"] >= 1


def test_constellation_gate_decisions_emitted() -> None:
    config = SolisConfig(cascade_threshold=0.35, runtime_gate_enabled=True)
    stars = SolisStarService(config=config)
    constellation = SolisConstellationService(star_service=stars, config=config)

    stars.create_star(star_id="ca", chain_id="public")
    stars.create_star(star_id="cb", chain_id="public")
    constellation.create_constellation(domain="civic", star_uris=["ca", "cb"])
    constellation.recompute_constellation("civic")

    uris = _gate_uris(stars.qso, "qso://solis.gate.constellation.")
    assert uris
    payload = stars.qso.read(uris[0])["state_layer"]
    assert payload["scope"] == "constellation"
    assert payload["stage"] in {"precommit", "postcommit"}
    assert payload["gate"] in {"gate1", "gate2", "gate3"}
    assert isinstance(payload["passed"], bool)

    health = _health_payload(stars.qso, "constellation")
    assert health["scope"] == "constellation"
    assert health["decision_event_count"] >= 1


def test_signal_gate_decisions_emitted() -> None:
    config = SolisConfig(runtime_gate_enabled=True)
    stars = SolisStarService(config=config)
    signals = SolisMetaSignalService(star_service=stars, config=config)

    stars.create_star(star_id="sg", chain_id="spherechain")
    stars.patch_star(
        star_uri_or_id="sg",
        delta={"mass": 0.2, "luminosity": 0.1, "entropy_index": 0.01, "magnetic_field": -0.005},
    )
    signals.emit_signals("sg")

    uris = _gate_uris(stars.qso, "qso://solis.gate.signal.")
    assert uris
    payload = stars.qso.read(uris[0])["state_layer"]
    assert payload["scope"] == "signal"
    assert payload["stage"] in {"precommit", "postcommit"}
    assert payload["gate"] in {"gate1", "gate2", "gate3"}
    assert isinstance(payload["passed"], bool)

    health = _health_payload(stars.qso, "signal")
    assert health["scope"] == "signal"
    assert health["decision_event_count"] >= 1


def test_gate_health_rollup_counts_and_rates() -> None:
    config = SolisConfig(runtime_gate_enabled=True)
    stars = SolisStarService(config=config)

    emit_gate_decision(
        qso=stars.qso,
        config=config,
        scope="star",
        stage="precommit",
        target_uri="qso://solis.star.r0",
        gate=GateResult(gate="gate1", passed=True, detail="ok"),
        context={"sample": 1},
    )
    emit_gate_decision(
        qso=stars.qso,
        config=config,
        scope="star",
        stage="precommit",
        target_uri="qso://solis.star.r0",
        gate=GateResult(gate="gate1", passed=False, detail="forced_fail"),
        context={"sample": 2},
    )
    emit_gate_decision(
        qso=stars.qso,
        config=config,
        scope="star",
        stage="postcommit",
        target_uri="qso://solis.star.r0",
        gate=GateResult(gate="gate2", passed=True, detail="ok"),
        context={"sample": 3},
    )

    health = _health_payload(stars.qso, "star")
    assert health["scope"] == "star"
    assert health["decision_uri_count"] == 2
    assert health["decision_event_count"] == 3
    assert health["pass_count"] == 2
    assert health["fail_count"] == 1
    assert health["pass_rate"] == pytest.approx(2 / 3)
    assert health["fail_rate"] == pytest.approx(1 / 3)
    assert health["ordered_gate_decision_uris"] == sorted(health["ordered_gate_decision_uris"])
    assert health["by_gate"] == [
        {
            "gate": "gate1",
            "pass_count": 1,
            "fail_count": 1,
            "total_count": 2,
            "pass_rate": pytest.approx(0.5),
            "fail_rate": pytest.approx(0.5),
        },
        {
            "gate": "gate2",
            "pass_count": 1,
            "fail_count": 0,
            "total_count": 1,
            "pass_rate": pytest.approx(1.0),
            "fail_rate": pytest.approx(0.0),
        },
    ]
    assert health["by_stage"] == [
        {
            "stage": "postcommit",
            "pass_count": 1,
            "fail_count": 0,
            "total_count": 1,
            "pass_rate": pytest.approx(1.0),
            "fail_rate": pytest.approx(0.0),
        },
        {
            "stage": "precommit",
            "pass_count": 1,
            "fail_count": 1,
            "total_count": 2,
            "pass_rate": pytest.approx(0.5),
            "fail_rate": pytest.approx(0.5),
        },
    ]


def test_gate_health_rollup_ordering_is_deterministic() -> None:
    config = SolisConfig(runtime_gate_enabled=True)
    first = SolisStarService(config=config)
    second = SolisStarService(config=config)

    decisions = [
        ("precommit", "qso://solis.star.ds0", GateResult(gate="gate2", passed=True, detail="ok")),
        ("postcommit", "qso://solis.star.ds1", GateResult(gate="gate1", passed=False, detail="forced_fail")),
        ("precommit", "qso://solis.star.ds2", GateResult(gate="gate3", passed=True, detail="ok")),
        ("postcommit", "qso://solis.star.ds0", GateResult(gate="gate2", passed=True, detail="ok")),
    ]

    for stage, target_uri, gate in decisions:
        emit_gate_decision(
            qso=first.qso,
            config=config,
            scope="star",
            stage=stage,
            target_uri=target_uri,
            gate=gate,
        )

    for stage, target_uri, gate in reversed(decisions):
        emit_gate_decision(
            qso=second.qso,
            config=config,
            scope="star",
            stage=stage,
            target_uri=target_uri,
            gate=gate,
        )

    first_health = _health_payload(first.qso, "star")
    second_health = _health_payload(second.qso, "star")

    assert first_health["ordered_gate_decision_uris"] == sorted(first_health["ordered_gate_decision_uris"])
    assert second_health["ordered_gate_decision_uris"] == sorted(second_health["ordered_gate_decision_uris"])
    assert first_health["by_gate"] == second_health["by_gate"]
    assert first_health["by_stage"] == second_health["by_stage"]
    assert first_health["pass_count"] == second_health["pass_count"]
    assert first_health["fail_count"] == second_health["fail_count"]
    assert first_health["pass_rate"] == second_health["pass_rate"]
    assert first_health["fail_rate"] == second_health["fail_rate"]
