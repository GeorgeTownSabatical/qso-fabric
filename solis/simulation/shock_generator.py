from __future__ import annotations

from typing import Dict


def deterministic_shock_pattern(step: int) -> Dict[str, float]:
    if step < 0:
        raise ValueError("step must be >= 0")
    return {
        "entropy_index": 0.01 * step,
        "magnetic_field": -0.005 * step,
    }


def deterministic_liquidity_shock(step: int) -> Dict[str, float]:
    return {
        "mass": 0.002 * step,
        "luminosity": 0.0015 * step,
    }
