from __future__ import annotations

from dataclasses import dataclass

from solis.physics.fixed_math import Fixed64
from solis.physics.stability_solver import StabilityField


@dataclass(frozen=True)
class RiskAssessment:
    allowed: bool
    collapse_threshold: Fixed64
    systemic_risk_index: Fixed64


def assess_runtime_risk(stability: StabilityField, collapse_threshold: Fixed64) -> RiskAssessment:
    allowed = stability.systemic_risk_index <= collapse_threshold
    return RiskAssessment(
        allowed=allowed,
        collapse_threshold=collapse_threshold,
        systemic_risk_index=stability.systemic_risk_index,
    )
