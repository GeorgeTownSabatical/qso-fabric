from __future__ import annotations

import pytest

from solis.config import SolisConfig
from solis.services.solis_star_service import SolisStarService


def test_runtime_gate3_blocks_when_proof_required_and_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SolisConfig(anchor_interval=2, runtime_gate_enabled=True, require_zk_proof=True)
    service = SolisStarService(config=config)
    service.create_star(star_id="gateproof", chain_id="spherechain")

    monkeypatch.setattr("solis.services.solis_star_service.verify_collapse_proof", lambda proof: False)

    with pytest.raises(ValueError, match="gate3 rejected"):
        service.patch_star(
            star_uri_or_id="gateproof",
            delta={"mass": 0.2, "luminosity": 0.1, "entropy_index": 0.02, "magnetic_field": -0.01},
            actor="gate-test",
        )


def test_runtime_gates_can_be_disabled_for_transition(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SolisConfig(anchor_interval=2, runtime_gate_enabled=False, require_zk_proof=True)
    service = SolisStarService(config=config)
    service.create_star(star_id="gatedisabled", chain_id="spherechain")

    monkeypatch.setattr("solis.services.solis_star_service.verify_collapse_proof", lambda proof: False)

    result = service.patch_star(
        star_uri_or_id="gatedisabled",
        delta={"mass": 0.2, "luminosity": 0.1, "entropy_index": 0.02, "magnetic_field": -0.01},
        actor="gate-test",
    )
    assert result["state"]["mass"] > 1.0


def test_runtime_post_commit_gate_rejects_missing_event_emission(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SolisConfig(anchor_interval=2, runtime_gate_enabled=True)
    service = SolisStarService(config=config)
    service.create_star(star_id="gatepost", chain_id="spherechain")

    monkeypatch.setattr(
        service,
        "_emit_stellar_event",
        lambda **kwargs: {},
    )

    with pytest.raises(ValueError, match="post-commit gate2 rejected"):
        service.patch_star(
            star_uri_or_id="gatepost",
            delta={"mass": 0.1, "luminosity": 0.1, "entropy_index": 0.01, "magnetic_field": -0.005},
            actor="gate-test",
        )

