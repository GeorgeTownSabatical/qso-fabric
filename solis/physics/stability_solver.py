from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from solis.physics.collapse_engine import collapse_probability_v1, stability_margin
from solis.physics.contagion_engine import snapshot as contagion_snapshot
from solis.physics.entropy_engine import entropy_gradient
from solis.physics.fixed_math import Fixed64


@dataclass(frozen=True)
class StabilityField:
    collapse_vector: dict[str, Fixed64]
    entropy_gradient: dict[str, Fixed64]
    systemic_risk_index: Fixed64
    stability_margin: Fixed64


def solve_stability_field(
    constellation_state: Mapping[str, Mapping[str, Fixed64]],
    *,
    steps: int = 1,
) -> StabilityField:
    collapse_vector: dict[str, Fixed64] = {}
    entropy_vec: dict[str, Fixed64] = {}

    for uri in sorted(constellation_state.keys()):
        state = constellation_state[uri]
        entropy = state.get("entropy_index", Fixed64.zero())
        magnetic = state.get("magnetic_field", Fixed64.one())
        fusion = state.get("fusion_rate", Fixed64.zero())
        prev_entropy = state.get("previous_entropy_index", entropy)

        collapse_vector[uri] = collapse_probability_v1(entropy, magnetic, fusion)
        entropy_vec[uri] = entropy_gradient(prev_entropy, entropy, steps=steps)

    c_snapshot = contagion_snapshot(collapse_vector)
    systemic = c_snapshot.contagion_index
    margin = stability_margin(systemic)

    return StabilityField(
        collapse_vector=collapse_vector,
        entropy_gradient=entropy_vec,
        systemic_risk_index=systemic,
        stability_margin=margin,
    )
