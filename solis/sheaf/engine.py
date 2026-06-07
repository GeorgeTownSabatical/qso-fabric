from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from solis.physics.fixed_math import Fixed64
from solis.physics.sheaf_model import InfluenceMatrix, SheafState, influence_matrix, make_sheaf_state, propagate
from solis.physics.stability_solver import StabilityField, solve_stability_field


@dataclass(frozen=True)
class SheafProjection:
    state: SheafState
    influence: InfluenceMatrix
    propagated: SheafState
    stability: StabilityField


def build_sheaf_projection(
    *,
    layer_fields: Mapping[str, Mapping[str, Fixed64]],
    constellation_state: Mapping[str, Mapping[str, Fixed64]],
    steps: int = 1,
) -> SheafProjection:
    state = make_sheaf_state(layer_fields)
    matrix = influence_matrix(state)
    projected = propagate(state, matrix)
    stability = solve_stability_field(constellation_state, steps=steps)
    return SheafProjection(
        state=state,
        influence=matrix,
        propagated=projected,
        stability=stability,
    )
