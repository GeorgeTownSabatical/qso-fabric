from __future__ import annotations

from typing import Dict, Iterable


def compute_liquidity_gravity(star_states: Iterable[dict]) -> float:
    states = list(star_states)
    if not states:
        return 0.0
    total_mass = sum(float(s.get("mass", 0.0)) for s in states)
    total_luminosity = sum(float(s.get("luminosity", 0.0)) for s in states)
    return (total_mass * 0.6) + (total_luminosity * 0.4)


def build_planetary_index(star_states: Iterable[dict]) -> Dict[str, float]:
    states = list(star_states)
    if not states:
        return {"liquidity_gravity": 0.0, "governance_resonance": 0.0, "collapse_wave": 0.0}

    liquidity_gravity = compute_liquidity_gravity(states)
    governance_resonance = sum(float(s.get("entropy_index", 0.0)) for s in states) / len(states)
    collapse_wave = sum(float(s.get("collapse_probability", 0.0)) for s in states) / len(states)

    return {
        "liquidity_gravity": liquidity_gravity,
        "governance_resonance": governance_resonance,
        "collapse_wave": collapse_wave,
    }
