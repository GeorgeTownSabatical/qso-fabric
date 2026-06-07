from __future__ import annotations

from dataclasses import dataclass

from solis.physics.fixed_math import Fixed64


@dataclass(frozen=True)
class EntropyVector:
    previous: Fixed64
    current: Fixed64
    delta: Fixed64
    gradient: Fixed64


def entropy_delta(previous: Fixed64, current: Fixed64) -> Fixed64:
    return current - previous


def entropy_gradient(previous: Fixed64, current: Fixed64, steps: int = 1) -> Fixed64:
    if steps <= 0:
        raise ValueError("steps must be > 0")
    return entropy_delta(previous, current) / Fixed64.from_int(steps)


def entropy_projection(current: Fixed64, delta: Fixed64) -> Fixed64:
    projected = current + delta
    if projected < Fixed64.zero():
        return Fixed64.zero()
    return projected


def entropy_vector(previous: Fixed64, current: Fixed64, steps: int = 1) -> EntropyVector:
    delta = entropy_delta(previous, current)
    gradient = entropy_gradient(previous, current, steps=steps)
    return EntropyVector(
        previous=previous,
        current=current,
        delta=delta,
        gradient=gradient,
    )
