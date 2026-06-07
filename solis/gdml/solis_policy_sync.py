from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from solis.projectors.stellar_projector_v1 import StellarState


class SolisPolicySync:
    """Applies GDML-distributed policy updates to stellar parameters."""

    def apply_policy(self, stellar_state: StellarState, policy: Mapping[str, Any]) -> StellarState:
        next_state = stellar_state

        if "fusion_adjustment" in policy:
            factor = float(policy["fusion_adjustment"])
            next_state = replace(next_state, fusion_rate=next_state.fusion_rate * factor)

        if "entropy_threshold" in policy:
            threshold = float(policy["entropy_threshold"])
            next_state = replace(next_state, entropy_index=min(next_state.entropy_index, threshold))

        if "magnetic_floor" in policy:
            floor = float(policy["magnetic_floor"])
            next_state = replace(next_state, magnetic_field=max(next_state.magnetic_field, floor))

        return next_state
