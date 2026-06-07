from __future__ import annotations

from solis.integration.gates import gate1_deterministic_replay_lock, gate2_invariant_enforcement_lock, gate3_zk_compatibility_lock


def test_gate1_replay_lock_passes() -> None:
    def reducer(state: dict, event: dict) -> dict:
        out = dict(state)
        out["sum"] = out.get("sum", 0) + int(event["x"])
        return out

    result = gate1_deterministic_replay_lock(
        initial_state={"sum": 0},
        events=[{"x": 1}, {"x": 2}, {"x": 3}],
        reducer=reducer,
    )
    assert result.passed


def test_gate2_and_gate3() -> None:
    assert gate2_invariant_enforcement_lock([]).passed
    assert not gate2_invariant_enforcement_lock(["A", "B"]).passed
    assert not gate2_invariant_enforcement_lock([], event_emitted=False).passed
    assert not gate2_invariant_enforcement_lock([], anchor_emitted=False).passed
    assert not gate2_invariant_enforcement_lock([], replay_verified=False).passed

    assert gate3_zk_compatibility_lock(formula_equal=True).passed
    assert not gate3_zk_compatibility_lock(formula_equal=False).passed
    assert not gate3_zk_compatibility_lock(formula_equal=True, proof_verified=False).passed
    assert not gate3_zk_compatibility_lock(formula_equal=True, fixed_point_only=False).passed


def test_gate1_requires_events() -> None:
    def reducer(state: dict, event: dict) -> dict:
        out = dict(state)
        out["sum"] = out.get("sum", 0) + int(event["x"])
        return out

    result = gate1_deterministic_replay_lock(
        initial_state={"sum": 0},
        events=[],
        reducer=reducer,
    )
    assert not result.passed
    assert result.detail == "no_events"
