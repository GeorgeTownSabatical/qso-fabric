from __future__ import annotations

import hashlib
import json
import os

import pytest

from solis.config import SolisConfig
from solis.services.solis_star_service import SolisStarService

EVENT_COUNT = int(os.getenv("SOLIS_NIGHTLY_REPLAY_EVENT_COUNT", "1000"))
NODE_COUNT = 3
STAR_ID = "spherechain"
EXPECTED_NIGHTLY_1000_STATE_HASH = "eda3b705472d8ccea2f14e8b270b2f5695ef5d123066426bf3c8ffae749ef673"
EXPECTED_NIGHTLY_1000_ROOT_HASH = "5f5cc09a9386f73867b6925cba67cfc609085f89f4f0bd6371f7a41eed1b3805"
EXPECTED_NIGHTLY_1000_ANCHOR_CHAIN_HASH = "b7083b72b1a88cc6e1266d232b0f3025643eda17c6584c7c44473d115bfe84a9"


def _hash_obj(obj: object) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_hex64(value: str) -> bool:
    if len(value) != 64:
        return False
    return all(ch in "0123456789abcdef" for ch in value.lower())


def _deterministic_delta(step: int) -> dict[str, float]:
    mass = 0.0009 + ((step % 13) * 0.00017)
    luminosity = 0.0011 + ((step % 11) * 0.00013)
    entropy = 0.00008 if (step % 7 == 0) else -0.00003
    magnetic = 0.00005 if (step % 5 == 0) else -0.00004
    return {
        "mass": mass,
        "luminosity": luminosity,
        "entropy_index": entropy,
        "magnetic_field": magnetic,
    }


@pytest.mark.nightly_replay
def test_multinode_replay_matrix_long_run_1000_events() -> None:
    config = SolisConfig(anchor_interval=8, runtime_gate_enabled=False)
    nodes = [SolisStarService(config=config) for _ in range(NODE_COUNT)]
    for node in nodes:
        node.create_star(star_id=STAR_ID, chain_id=STAR_ID)

    for idx in range(EVENT_COUNT):
        delta = _deterministic_delta(idx)
        for node in nodes:
            node.patch_star(star_uri_or_id=STAR_ID, delta=delta, actor="replay-nightly")

    state_hashes = {_hash_obj(node.get_star(STAR_ID)["state_layer"]) for node in nodes}
    roots = {node.merkle_anchor.root() for node in nodes}
    assert len(state_hashes) == 1
    assert len(roots) == 1
    state_hash = next(iter(state_hashes))
    root_hash = next(iter(roots))
    assert _is_hex64(state_hash)
    assert _is_hex64(root_hash)

    anchor_epoch = len(nodes[0].merkle_anchor.event_hashes) // config.anchor_interval
    assert anchor_epoch > 0
    anchor_hashes_by_epoch: list[str] = []
    for epoch in range(1, anchor_epoch + 1):
        uri = f"qso://solis.anchor.{epoch}"
        anchor_hashes = {_hash_obj(node.qso.read(uri)["state_layer"]) for node in nodes}
        assert len(anchor_hashes) == 1
        anchor_hashes_by_epoch.append(next(iter(anchor_hashes)))

    anchor_chain_hash = _hash_obj(anchor_hashes_by_epoch)
    assert _is_hex64(anchor_chain_hash)
    if EVENT_COUNT == 1000:
        expected = {
            "state": EXPECTED_NIGHTLY_1000_STATE_HASH,
            "root": EXPECTED_NIGHTLY_1000_ROOT_HASH,
            "anchor_chain": EXPECTED_NIGHTLY_1000_ANCHOR_CHAIN_HASH,
        }
        actual = {
            "state": state_hash,
            "root": root_hash,
            "anchor_chain": anchor_chain_hash,
        }
        assert actual == expected
