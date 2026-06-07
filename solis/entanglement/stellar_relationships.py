from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class StellarRelationshipEffect:
    event_type: str
    magnitude: float
    delta: Dict[str, float]
    inverse_delta: Dict[str, float]


def relationship_delta(event_type: str, magnitude: float = 1.0, reverse: bool = False) -> StellarRelationshipEffect:
    """Deterministic, reversible mappings for Solis entanglement propagation."""

    event_key = event_type.strip().lower()
    if magnitude < 0:
        raise ValueError("magnitude must be >= 0")

    forward = _forward_delta(event_key, magnitude)
    inverse = _invert_delta(forward)

    delta = inverse if reverse else forward
    inverse_delta = forward if reverse else inverse

    return StellarRelationshipEffect(
        event_type=event_key,
        magnitude=magnitude,
        delta=delta,
        inverse_delta=inverse_delta,
    )


def _forward_delta(event_key: str, magnitude: float) -> Dict[str, float]:
    if event_key == "validator_slashing":
        # Validator slashing reduces magnetic field coherence.
        return {"magnetic_field": -0.08 * magnitude}

    if event_key == "governance_vote_spike":
        # Vote spikes increase entropy due to governance turbulence.
        return {"entropy_index": 0.05 * magnitude}

    if event_key == "contract_congestion":
        # Congestion spikes thermal pressure through energy throughput strain.
        return {
            "luminosity": 0.12 * magnitude,
            "entropy_index": 0.01 * magnitude,
            "core_temp_spike": 45.0 * magnitude,
        }

    if event_key == "token_mint":
        # Minting increases mass in economic-stellar mapping.
        return {"mass": 0.20 * magnitude}

    raise ValueError(f"unsupported entanglement event type: {event_key}")


def _invert_delta(delta: Dict[str, float]) -> Dict[str, float]:
    return {key: -value for key, value in delta.items()}
