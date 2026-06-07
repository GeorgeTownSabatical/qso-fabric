from __future__ import annotations

from solis.physics.fixed_math import Fixed64
from solis.physics.invariants import (
    GlobalState,
    InvariantLimits,
    evaluate_agent_invariants,
    evaluate_constellation_invariants,
    evaluate_global_invariants,
)


def _state(
    *,
    capital: str,
    entropy: str,
    collapse: str,
    leverage: str,
    contagion: str,
) -> GlobalState:
    return GlobalState(
        capital_total=Fixed64.from_str(capital),
        entropy_index=Fixed64.from_str(entropy),
        collapse_probability=Fixed64.from_str(collapse),
        leverage_ratio=Fixed64.from_str(leverage),
        contagion_index=Fixed64.from_str(contagion),
    )


def test_global_invariant_skeleton_passes_within_limits() -> None:
    prev = _state(capital="100.0", entropy="0.10", collapse="0.20", leverage="1.5", contagion="0.30")
    curr = _state(capital="100.0", entropy="0.12", collapse="0.25", leverage="1.6", contagion="0.40")
    limits = InvariantLimits(
        max_entropy_growth=Fixed64.from_str("0.05"),
        max_collapse_probability=Fixed64.from_str("0.35"),
        max_leverage_ratio=Fixed64.from_str("2.00"),
        max_contagion_index=Fixed64.from_str("0.60"),
        capital_tolerance=Fixed64.from_str("0.00"),
    )

    results = evaluate_global_invariants(prev, curr, limits)
    assert all(item.passed for item in results)


def test_global_invariant_skeleton_flags_exceedances() -> None:
    prev = _state(capital="100.0", entropy="0.10", collapse="0.20", leverage="1.5", contagion="0.30")
    curr = _state(capital="105.0", entropy="0.30", collapse="0.80", leverage="3.1", contagion="0.91")
    limits = InvariantLimits(
        max_entropy_growth=Fixed64.from_str("0.05"),
        max_collapse_probability=Fixed64.from_str("0.35"),
        max_leverage_ratio=Fixed64.from_str("2.00"),
        max_contagion_index=Fixed64.from_str("0.60"),
        capital_tolerance=Fixed64.from_str("0.10"),
    )

    results = evaluate_global_invariants(prev, curr, limits)
    assert any(not item.passed for item in results)


def test_constellation_and_agent_skeletons() -> None:
    limits = InvariantLimits(
        max_entropy_growth=Fixed64.from_str("1.00"),
        max_collapse_probability=Fixed64.from_str("1.00"),
        max_leverage_ratio=Fixed64.from_str("10.0"),
        max_contagion_index=Fixed64.from_str("1.00"),
    )

    constellation_results = evaluate_constellation_invariants(
        member_states={
            "qso://solis.star.a": _state(
                capital="1.0", entropy="0.1", collapse="0.2", leverage="1.0", contagion="0.2"
            )
        },
        limits=limits,
    )
    assert constellation_results

    assert evaluate_agent_invariants({"risk_version": "v1", "max_drawdown": "0.1", "collapse_threshold": "0.3"})[0].passed
    assert not evaluate_agent_invariants({"risk_version": "v1"})[0].passed
