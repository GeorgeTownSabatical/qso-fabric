from __future__ import annotations

from typing import Mapping


class SolisRewardAdapter:
    """Converts stellar metrics into GDML reward signals."""

    def compute_reward(self, stellar_state: Mapping[str, float] | object) -> float:
        def _get(key: str) -> float:
            if isinstance(stellar_state, Mapping):
                return float(stellar_state.get(key, 0.0))
            return float(getattr(stellar_state, key, 0.0))

        stability_score = 1.0 - _get("collapse_probability")
        efficiency_score = _get("fusion_rate")
        entropy_penalty = _get("entropy_index")

        return (0.5 * stability_score) + (0.4 * efficiency_score) - (0.3 * entropy_penalty)
