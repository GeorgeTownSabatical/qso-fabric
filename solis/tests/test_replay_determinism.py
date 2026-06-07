from __future__ import annotations

import hashlib
import json

from solis.config import SolisConfig
from solis.services.solis_star_service import SolisStarService


def _hash_obj(obj: object) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


EXPECTED_LONG_SEQUENCE_STATE_HASH = "8fa46523c4104a6276a01dae9abd7c846bee3a13aba28b0ea185ca60f3a22347"
EXPECTED_LONG_SEQUENCE_ROOT_HASH = "13b109405c3305bb27e084de269be8328a52237f3bf081f2ca3c4ca52f357cf5"
EXPECTED_LONG_SEQUENCE_ANCHOR_CHAIN_HASH = "200b92d49ee4c1614734f77bad8c5eba337cdd0ae771a2a7df7a82c44a7572df"


def test_replay_determinism_final_state_and_anchor() -> None:
    config = SolisConfig(anchor_interval=2)
    node_a = SolisStarService(config=config)
    node_b = SolisStarService(config=config)

    node_a.create_star(star_id="spherechain", chain_id="spherechain")
    node_b.create_star(star_id="spherechain", chain_id="spherechain")

    delta = {"mass": 0.8, "luminosity": 1.1, "entropy_index": 0.05, "magnetic_field": -0.03}
    node_a.patch_star(star_uri_or_id="spherechain", delta=delta, actor="replay")
    node_b.patch_star(star_uri_or_id="spherechain", delta=delta, actor="replay")

    state_a = node_a.get_star("spherechain")["state_layer"]
    state_b = node_b.get_star("spherechain")["state_layer"]
    assert _hash_obj(state_a) == _hash_obj(state_b)

    root_a = node_a.merkle_anchor.root()
    root_b = node_b.merkle_anchor.root()
    assert root_a == root_b

    anchor_uri = "qso://solis.anchor.1"
    anchor_a = node_a.qso.read(anchor_uri)["state_layer"]
    anchor_b = node_b.qso.read(anchor_uri)["state_layer"]
    assert _hash_obj(anchor_a) == _hash_obj(anchor_b)


def _deterministic_delta(step: int) -> dict[str, object]:
    # Deterministic, bounded sequence with mixed numeric representations.
    mass_value = 0.001 + ((step % 5) * 0.00015)
    luminosity_value = 0.0012 + ((step % 7) * 0.00011)
    entropy_value: object = "8e-05" if (step % 9 == 0) else "-3e-05"
    magnetic_value: object = "5e-05" if (step % 4 == 0) else -0.00004

    mass: object = format(mass_value, ".12e") if (step % 2 == 0) else mass_value
    luminosity: object = format(luminosity_value, ".12e") if (step % 3 == 0) else luminosity_value

    if step % 17 == 0:
        entropy_value = "1e-24"
    if step % 23 == 0:
        magnetic_value = "-1e-24"

    return {
        "mass": mass,
        "luminosity": luminosity,
        "entropy_index": entropy_value,
        "magnetic_field": magnetic_value,
    }


def test_replay_determinism_long_sequence_three_nodes() -> None:
    config = SolisConfig(anchor_interval=8, runtime_gate_enabled=False)
    nodes = [SolisStarService(config=config) for _ in range(3)]
    for node in nodes:
        node.create_star(star_id="spherechain", chain_id="spherechain")

    for idx in range(360):
        delta = _deterministic_delta(idx)
        for node in nodes:
            node.patch_star(star_uri_or_id="spherechain", delta=delta, actor="replay-long")

    state_hashes = {_hash_obj(node.get_star("spherechain")["state_layer"]) for node in nodes}
    roots = {node.merkle_anchor.root() for node in nodes}
    assert state_hashes == {EXPECTED_LONG_SEQUENCE_STATE_HASH}
    assert roots == {EXPECTED_LONG_SEQUENCE_ROOT_HASH}

    anchor_epoch = len(nodes[0].merkle_anchor.event_hashes) // config.anchor_interval
    assert anchor_epoch > 0
    anchor_hashes: list[str] = []
    for epoch in range(1, anchor_epoch + 1):
        uri = f"qso://solis.anchor.{epoch}"
        row = tuple(_hash_obj(node.qso.read(uri)["state_layer"]) for node in nodes)
        assert len(set(row)) == 1
        anchor_hashes.append(row[0])
    assert _hash_obj(anchor_hashes) == EXPECTED_LONG_SEQUENCE_ANCHOR_CHAIN_HASH
