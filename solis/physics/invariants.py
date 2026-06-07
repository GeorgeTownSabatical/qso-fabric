from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from solis.physics.fixed_math import Fixed64


@dataclass(frozen=True)
class InvariantResult:
    name: str
    passed: bool
    reason_code: str
    detail: str = ""


@dataclass(frozen=True)
class InvariantLimits:
    max_entropy_growth: Fixed64
    max_collapse_probability: Fixed64
    max_leverage_ratio: Fixed64
    max_contagion_index: Fixed64
    capital_tolerance: Fixed64 = Fixed64(raw=0)


@dataclass(frozen=True)
class GlobalState:
    capital_total: Fixed64
    entropy_index: Fixed64
    collapse_probability: Fixed64
    leverage_ratio: Fixed64
    contagion_index: Fixed64


def _ok(name: str, reason_code: str = "OK", detail: str = "") -> InvariantResult:
    return InvariantResult(name=name, passed=True, reason_code=reason_code, detail=detail)


def _fail(name: str, reason_code: str, detail: str = "") -> InvariantResult:
    return InvariantResult(name=name, passed=False, reason_code=reason_code, detail=detail)


def invariant_capital_conservation(
    previous_capital: Fixed64,
    current_capital: Fixed64,
    tolerance: Fixed64,
) -> InvariantResult:
    drift = abs(current_capital - previous_capital)
    if drift <= tolerance:
        return _ok("capital_conservation")
    return _fail("capital_conservation", "CAPITAL_DRIFT", detail=f"drift={drift.to_str(18)}")


def invariant_collapse_bound(collapse_probability: Fixed64, max_probability: Fixed64) -> InvariantResult:
    if collapse_probability <= max_probability:
        return _ok("collapse_bound")
    return _fail("collapse_bound", "COLLAPSE_BOUND_EXCEEDED")


def invariant_entropy_growth(
    previous_entropy: Fixed64,
    current_entropy: Fixed64,
    max_growth: Fixed64,
) -> InvariantResult:
    growth = current_entropy - previous_entropy
    if growth <= max_growth:
        return _ok("entropy_growth")
    return _fail("entropy_growth", "ENTROPY_GROWTH_EXCEEDED", detail=f"growth={growth.to_str(18)}")


def invariant_leverage_envelope(leverage_ratio: Fixed64, max_leverage: Fixed64) -> InvariantResult:
    if leverage_ratio <= max_leverage:
        return _ok("leverage_envelope")
    return _fail("leverage_envelope", "LEVERAGE_LIMIT_EXCEEDED")


def invariant_contagion_threshold(contagion_index: Fixed64, max_contagion: Fixed64) -> InvariantResult:
    if contagion_index <= max_contagion:
        return _ok("contagion_threshold")
    return _fail("contagion_threshold", "CONTAGION_THRESHOLD_EXCEEDED")


def evaluate_global_invariants(
    previous_state: GlobalState,
    current_state: GlobalState,
    limits: InvariantLimits,
) -> list[InvariantResult]:
    return [
        invariant_capital_conservation(
            previous_capital=previous_state.capital_total,
            current_capital=current_state.capital_total,
            tolerance=limits.capital_tolerance,
        ),
        invariant_entropy_growth(
            previous_entropy=previous_state.entropy_index,
            current_entropy=current_state.entropy_index,
            max_growth=limits.max_entropy_growth,
        ),
        invariant_collapse_bound(
            collapse_probability=current_state.collapse_probability,
            max_probability=limits.max_collapse_probability,
        ),
        invariant_leverage_envelope(
            leverage_ratio=current_state.leverage_ratio,
            max_leverage=limits.max_leverage_ratio,
        ),
        invariant_contagion_threshold(
            contagion_index=current_state.contagion_index,
            max_contagion=limits.max_contagion_index,
        ),
    ]


def evaluate_constellation_invariants(
    *,
    member_states: Mapping[str, GlobalState],
    limits: InvariantLimits,
) -> list[InvariantResult]:
    """Skeleton for constellation-level checks.

    Phase-1 behavior: reduce member states through global invariant checks using
    deterministic baseline-zero previous states.
    """

    results: list[InvariantResult] = []
    zero = GlobalState(
        capital_total=Fixed64.zero(),
        entropy_index=Fixed64.zero(),
        collapse_probability=Fixed64.zero(),
        leverage_ratio=Fixed64.zero(),
        contagion_index=Fixed64.zero(),
    )

    for member_uri in sorted(member_states.keys()):
        state = member_states[member_uri]
        for row in evaluate_global_invariants(zero, state, limits):
            results.append(
                InvariantResult(
                    name=f"{member_uri}:{row.name}",
                    passed=row.passed,
                    reason_code=row.reason_code,
                    detail=row.detail,
                )
            )

    if not member_states:
        results.append(_fail("constellation_membership", "NO_MEMBERS"))
    return results


def evaluate_agent_invariants(policy: Mapping[str, object]) -> list[InvariantResult]:
    """Phase-1 skeleton for developer-layer policy declarations."""

    required = {
        "max_drawdown",
        "collapse_threshold",
        "risk_version",
    }

    missing = sorted(key for key in required if key not in policy)
    if missing:
        return [
            _fail(
                "agent_policy_schema",
                "AGENT_POLICY_MISSING_FIELDS",
                detail=",".join(missing),
            )
        ]

    return [_ok("agent_policy_schema")]
