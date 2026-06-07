from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from qso_xr.knowledge_lattice import ConsistencyConflict, KnowledgeLattice


def _hash_event(event: dict) -> str:
    payload = {key: event[key] for key in event if key != "hash"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_qso_xr_knowledge_lattice_fail_closed_then_approved_merge(tmp_path: Path) -> None:
    lattice = KnowledgeLattice(tmp_path / "knowledge")
    lattice.append_claim(section="entity.alpha", claim_id="c1", statement="state is stable", confidence=0.7)

    with pytest.raises(ConsistencyConflict):
        lattice.merge_sandbox(
            branch_name="sandbox-denied",
            claims=[{"section": "entity.alpha", "claim_id": "c1", "statement": "state is unstable", "confidence": 0.8}],
            vote_approved=False,
        )

    report = lattice.merge_sandbox(
        branch_name="sandbox-approved",
        claims=[
            {"section": "entity.alpha", "claim_id": "c1", "statement": "state is unstable", "confidence": 0.8},
            {"section": "entity.beta", "claim_id": "c2", "statement": "new claim", "confidence": 0.6},
        ],
        vote_approved=True,
    )
    assert report["approved"] is True
    assert report["new_claims"] == 1
    assert report["modified_claims"] == 1
    assert report["conflict_count"] == 1
    assert report["knowledge_curvature"] == 1.0
    assert report["version_id"] is not None
    assert Path(report["version_path"]).exists()

    lines = [line.strip() for line in lattice.events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    prev_hash = "GENESIS"
    for line in lines:
        event = json.loads(line)
        assert event["prev_hash"] == prev_hash
        assert event["hash"] == _hash_event(event)
        prev_hash = event["hash"]
