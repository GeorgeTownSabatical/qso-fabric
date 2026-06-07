from __future__ import annotations

from dataclasses import dataclass

from solis.projectors.stellar_projector_v1 import StellarState


@dataclass(frozen=True)
class InstabilityAssessment:
    instability_index: float
    drift_velocity: float
    phase: str
    cascade_risk: float
    collapse_imminent: bool


def assess_instability(current: StellarState, previous: StellarState | None = None) -> InstabilityAssessment:
    entropy_component = max(current.entropy_index, 0.0) * 0.5
    magnetic_component = (1.0 - current.magnetic_field) * 0.2
    collapse_component = current.collapse_probability * 0.3

    instability = _clamp(entropy_component + magnetic_component + collapse_component)

    drift = 0.0
    if previous is not None:
        drift = current.collapse_probability - previous.collapse_probability

    cascade_risk = _clamp(instability + max(drift, 0.0))

    if instability >= 0.75:
        phase = "critical"
    elif instability >= 0.40:
        phase = "warning"
    else:
        phase = "stable"

    return InstabilityAssessment(
        instability_index=instability,
        drift_velocity=drift,
        phase=phase,
        cascade_risk=cascade_risk,
        collapse_imminent=current.collapse_probability >= 0.9,
    )


def _clamp(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value
