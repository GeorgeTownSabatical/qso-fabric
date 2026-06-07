from __future__ import annotations

from dataclasses import dataclass
from typing import List

from solis.projectors.stellar_projector_v1 import StellarState
from solis.simulation.cascade_simulator import simulate_cascade


@dataclass(frozen=True)
class DeterministicRun:
    run_id: int
    final_state: StellarState


def run_deterministic_monte(initial: StellarState, steps: int, runs: int) -> List[DeterministicRun]:
    if runs <= 0:
        raise ValueError("runs must be > 0")

    outputs: List[DeterministicRun] = []
    for run_id in range(runs):
        # Deterministic run family: same model, shifted step horizon.
        timeline = simulate_cascade(initial, steps + run_id)
        outputs.append(DeterministicRun(run_id=run_id, final_state=timeline[-1]))
    return outputs
