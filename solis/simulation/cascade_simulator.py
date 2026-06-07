from __future__ import annotations

from typing import Dict, Iterable, List

from solis.projectors.stellar_projector_v1 import StellarState, project_stellar_v1
from solis.simulation.shock_generator import deterministic_liquidity_shock, deterministic_shock_pattern


def simulate_cascade(initial: StellarState, steps: int) -> List[StellarState]:
    if steps <= 0:
        raise ValueError("steps must be > 0")

    timeline: List[StellarState] = [initial]
    current = initial

    for step in range(1, steps + 1):
        shock = deterministic_shock_pattern(step)
        liquidity = deterministic_liquidity_shock(step)
        delta: Dict[str, float] = {
            "entropy_index": shock["entropy_index"],
            "magnetic_field": shock["magnetic_field"],
            "mass": liquidity["mass"],
            "luminosity": liquidity["luminosity"],
        }
        current = project_stellar_v1(current, delta)
        timeline.append(current)

    return timeline


def collapse_threshold_map(states: Iterable[StellarState], threshold: float) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for idx, state in enumerate(states):
        if state.collapse_probability >= threshold:
            out[idx] = state.collapse_probability
    return out
