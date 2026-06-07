from __future__ import annotations

from typing import Dict

from solis.projectors.stellar_projector_v1 import StellarState
from solis.simulation.cascade_simulator import collapse_threshold_map, simulate_cascade


def build_stress_report(initial: StellarState, steps: int = 10_000, threshold: float = 0.8) -> Dict[str, object]:
    timeline = simulate_cascade(initial, steps)
    threshold_map = collapse_threshold_map(timeline, threshold)

    recovery_latency = _recovery_latency(timeline, threshold)
    contagion_index = sum(state.collapse_probability for state in timeline) / len(timeline)

    return {
        "steps": steps,
        "collapse_threshold_map": threshold_map,
        "recovery_latency": recovery_latency,
        "contagion_index": contagion_index,
    }


def _recovery_latency(timeline: list[StellarState], threshold: float) -> int:
    peak_idx = max(range(len(timeline)), key=lambda i: timeline[i].collapse_probability)
    for idx in range(peak_idx, len(timeline)):
        if timeline[idx].collapse_probability < threshold:
            return idx - peak_idx
    return len(timeline) - 1 - peak_idx
