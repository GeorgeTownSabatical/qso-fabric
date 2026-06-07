from __future__ import annotations

from typing import Dict, Iterable


def governance_resonance(star_states: Iterable[dict]) -> float:
    states = list(star_states)
    if not states:
        return 0.0
    entropy = [float(state.get("entropy_index", 0.0)) for state in states]
    magnetic = [float(state.get("magnetic_field", 0.0)) for state in states]
    return (sum(entropy) / len(entropy)) * (1.0 - (sum(magnetic) / len(magnetic)))


def collapse_wave_propagation(star_states: Iterable[dict]) -> Dict[str, float]:
    states = list(star_states)
    if not states:
        return {"wave_velocity": 0.0, "wave_pressure": 0.0}

    collapse = [float(state.get("collapse_probability", 0.0)) for state in states]
    entropy = [float(state.get("entropy_index", 0.0)) for state in states]
    velocity = sum(collapse) / len(collapse)
    pressure = (sum(entropy) / len(entropy)) * velocity
    return {"wave_velocity": velocity, "wave_pressure": pressure}
