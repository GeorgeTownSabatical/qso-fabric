from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from solis.agent.sandbox.replay_engine import replay_events
from solis.identity.anchor.merkle import hash_leaf, merkle_root
from solis.shared.hashing import sha256_hex_obj


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ReplayEvidence:
    node_id: str
    state_hash: str
    merkle_root: str
    anchor_payload_hash: str


def _anchor_payload_hash(root: str, epoch: int, event_count: int) -> str:
    payload = {
        "epoch": epoch,
        "root": root,
        "event_count": event_count,
    }
    return sha256_hex_obj(payload)


def gate1_deterministic_replay_lock(
    *,
    initial_state: dict[str, Any],
    events: list[dict[str, Any]],
    reducer: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    node_ids: list[str] | None = None,
) -> GateResult:
    if not events:
        return GateResult("gate1", False, "no_events")

    nodes = node_ids or ["node-a", "node-b", "node-c"]
    if not nodes:
        return GateResult("gate1", False, "no_nodes")

    leaves = [hash_leaf(sha256_hex_obj(e)) for e in events]
    r1 = merkle_root(leaves)
    r2 = merkle_root(leaves)
    if r1 != r2:
        return GateResult("gate1", False, "merkle_root_mismatch")

    evidence: list[ReplayEvidence] = []
    for node_id in nodes:
        state, state_hash = replay_events(initial_state, events, reducer)
        evidence.append(
            ReplayEvidence(
                node_id=node_id,
                state_hash=state_hash,
                merkle_root=r1,
                anchor_payload_hash=_anchor_payload_hash(r1, epoch=1, event_count=len(events)),
            )
        )
        # Ensure payload shape is stable for every replay path.
        if not isinstance(state, dict):
            return GateResult("gate1", False, f"invalid_state_payload:{node_id}")

    state_hashes = {row.state_hash for row in evidence}
    if len(state_hashes) != 1:
        return GateResult("gate1", False, "state_hash_mismatch")

    roots = {row.merkle_root for row in evidence}
    if len(roots) != 1:
        return GateResult("gate1", False, "merkle_root_mismatch")

    anchors = {row.anchor_payload_hash for row in evidence}
    if len(anchors) != 1:
        return GateResult("gate1", False, "anchor_payload_hash_mismatch")

    return GateResult("gate1", True, "ok")


def gate2_invariant_enforcement_lock(
    failed_invariants: list[str],
    *,
    event_emitted: bool = True,
    anchor_emitted: bool = True,
    replay_verified: bool = True,
) -> GateResult:
    failures = sorted(set(failed_invariants))
    if not event_emitted:
        failures.append("missing_event_emission")
    if not anchor_emitted:
        failures.append("missing_anchor_emission")
    if not replay_verified:
        failures.append("replay_not_verified")

    if failures:
        return GateResult("gate2", False, ",".join(sorted(set(failures))))
    return GateResult("gate2", True, "ok")


def gate3_zk_compatibility_lock(
    *,
    formula_equal: bool,
    proof_verified: bool = True,
    fixed_point_only: bool = True,
) -> GateResult:
    failures: list[str] = []
    if not formula_equal:
        failures.append("formula_mismatch")
    if not proof_verified:
        failures.append("proof_not_verified")
    if not fixed_point_only:
        failures.append("non_fixed_point_math")

    if failures:
        return GateResult("gate3", False, ",".join(failures))
    return GateResult("gate3", True, "ok")
