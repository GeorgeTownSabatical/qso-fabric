from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from solis.config import SolisConfig
from solis.services.solis_star_service import SolisStarService

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
DATASET_FILES = {
    "dataset_alpha": FIXTURES_DIR / "replay_dataset_alpha.json",
    "dataset_beta": FIXTURES_DIR / "replay_dataset_beta.json",
}


def _hash_obj(obj: Any) -> str:
    encoded = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _load_deltas(dataset_name: str) -> list[dict[str, float]]:
    payload = json.loads(DATASET_FILES[dataset_name].read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"invalid replay dataset: {dataset_name}")

    out: list[dict[str, float]] = []
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError(f"invalid replay row in dataset: {dataset_name}")
        out.append(
            {
                "mass": float(row.get("mass", 0.0)),
                "luminosity": float(row.get("luminosity", 0.0)),
                "entropy_index": float(row.get("entropy_index", 0.0)),
                "magnetic_field": float(row.get("magnetic_field", 0.0)),
            }
        )
    return out


def _run_node(star_id: str, deltas: list[dict[str, float]]) -> tuple[str, str, str]:
    service = SolisStarService(config=SolisConfig(anchor_interval=2))
    service.create_star(star_id=star_id, chain_id=star_id)
    for delta in deltas:
        service.patch_star(star_uri_or_id=star_id, delta=delta, actor="replay-matrix")

    final_state = service.get_star(star_id)["state_layer"]
    state_hash = _hash_obj(final_state)
    root_hash = service.merkle_anchor.root()

    anchor_payload = service.qso.read("qso://solis.anchor.1")["state_layer"]
    anchor_hash = _hash_obj(anchor_payload)
    return state_hash, root_hash, anchor_hash


@pytest.mark.parametrize("star_id", ["spherechain", "publicchain", "uhha"])
@pytest.mark.parametrize("dataset_name", sorted(DATASET_FILES), ids=sorted(DATASET_FILES))
def test_multinode_replay_matrix_consistency(star_id: str, dataset_name: str) -> None:
    deltas = _load_deltas(dataset_name)
    matrix = [_run_node(star_id, deltas) for _ in range(3)]
    state_hashes = {row[0] for row in matrix}
    roots = {row[1] for row in matrix}
    anchor_hashes = {row[2] for row in matrix}

    assert len(state_hashes) == 1
    assert len(roots) == 1
    assert len(anchor_hashes) == 1
