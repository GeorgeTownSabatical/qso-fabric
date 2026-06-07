from __future__ import annotations

import pytest

from solis.agent.runtime.policy_guard import PolicyGuard
from solis.physics.fixed_math import Fixed64
from solis.physics.invariants import InvariantLimits


def _limits() -> InvariantLimits:
    return InvariantLimits(
        max_entropy_growth=Fixed64.from_str("0.20"),
        max_collapse_probability=Fixed64.from_str("0.50"),
        max_leverage_ratio=Fixed64.from_str("2.00"),
        max_contagion_index=Fixed64.from_str("0.60"),
        capital_tolerance=Fixed64.from_str("10.00"),
    )


def test_policy_guard_allows_safe_transition() -> None:
    guard = PolicyGuard(limits=_limits(), collapse_consistency_tolerance=Fixed64.from_str("0.10"))

    current = {
        "mass": 1.0,
        "entropy_index": 0.1,
        "magnetic_field": 0.9,
        "fusion_rate": 1.0,
        "collapse_probability": 0.01,
    }
    proposed = {
        "mass": 1.2,
        "entropy_index": 0.2,
        "magnetic_field": 0.9,
        "fusion_rate": 1.0,
        "collapse_probability": 0.02,
    }

    guard.validate_transition(current, proposed)


def test_policy_guard_rejects_formula_mismatch() -> None:
    guard = PolicyGuard(limits=_limits(), collapse_consistency_tolerance=Fixed64.from_str("0.00001"))

    current = {
        "mass": 1.0,
        "entropy_index": 0.1,
        "magnetic_field": 0.9,
        "fusion_rate": 1.0,
        "collapse_probability": 0.01,
    }
    proposed = {
        "mass": 1.2,
        "entropy_index": 0.2,
        "magnetic_field": 0.9,
        "fusion_rate": 1.0,
        "collapse_probability": 0.99,
    }

    with pytest.raises(ValueError, match="COLLAPSE_FORMULA_MISMATCH"):
        guard.validate_transition(current, proposed)


def test_policy_guard_rejects_negative_mass_and_bound_violations() -> None:
    guard = PolicyGuard(limits=_limits())

    with pytest.raises(ValueError, match="MASS_NON_POSITIVE"):
        guard.validate_transition({"mass": 1.0}, {"mass": -1.0, "entropy_index": 0.0, "magnetic_field": 1.0, "fusion_rate": 1.0})

    with pytest.raises(ValueError, match="COLLAPSE_BOUND_EXCEEDED"):
        guard.validate_transition(
            {
                "mass": 1.0,
                "entropy_index": 0.1,
                "magnetic_field": 0.9,
                "fusion_rate": 1.0,
                "collapse_probability": 0.01,
            },
            {
                "mass": 1.0,
                "entropy_index": 0.6,
                "magnetic_field": -2.0,
                "fusion_rate": 1.0,
                "collapse_probability": 1.0,
            },
        )


def test_policy_guard_rejects_disallowed_transition_fields_with_explicit_reason() -> None:
    guard = PolicyGuard(limits=_limits())
    current = {
        "mass": 1.0,
        "entropy_index": 0.1,
        "magnetic_field": 0.9,
        "fusion_rate": 1.0,
        "collapse_probability": 0.01,
    }
    proposed = {
        "mass": 1.1,
        "entropy_index": 0.2,
        "magnetic_field": 0.9,
        "fusion_rate": 1.0,
        "collapse_probability": 0.02,
        "unsafe_field": 123,
    }

    decision = guard.evaluate_transition(current, proposed)
    assert decision.allowed is False
    assert "FIELD_NOT_ALLOWED:unsafe_field" in decision.reason_codes

    with pytest.raises(ValueError, match="FIELD_NOT_ALLOWED:unsafe_field"):
        guard.validate_transition(current, proposed)


def test_policy_guard_deterministic_for_identical_inputs() -> None:
    guard = PolicyGuard(limits=_limits(), collapse_consistency_tolerance=Fixed64.from_str("0.10"))
    current = {
        "mass": 1.0,
        "entropy_index": 0.1,
        "magnetic_field": 0.9,
        "fusion_rate": 1.0,
        "collapse_probability": 0.01,
    }
    proposed = {
        "mass": 1.2,
        "entropy_index": 0.2,
        "magnetic_field": 0.9,
        "fusion_rate": 1.0,
        "collapse_probability": 0.02,
    }
    decision_a = guard.evaluate_transition(current, proposed)
    decision_b = guard.evaluate_transition(current, proposed)
    assert decision_a == decision_b
