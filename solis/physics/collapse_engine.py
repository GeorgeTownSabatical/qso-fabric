from __future__ import annotations

from dataclasses import dataclass

from solis.physics.fixed_math import Fixed64


@dataclass(frozen=True)
class CollapseProjection:
    entropy: Fixed64
    magnetic: Fixed64
    fusion: Fixed64
    instability: Fixed64
    collapse_probability: Fixed64
    stability_margin: Fixed64


def _clamp01(value: Fixed64) -> Fixed64:
    if value < Fixed64.zero():
        return Fixed64.zero()
    if value > Fixed64.one():
        return Fixed64.one()
    return value


def collapse_probability_v1(entropy: Fixed64, magnetic: Fixed64, fusion: Fixed64) -> Fixed64:
    instability = entropy * (Fixed64.one() - magnetic)
    return _clamp01(instability * fusion)


def stability_margin(collapse_probability: Fixed64) -> Fixed64:
    return _clamp01(Fixed64.one() - collapse_probability)


def collapse_drift(previous: Fixed64, current: Fixed64) -> Fixed64:
    return current - previous


def project_collapse(entropy: Fixed64, magnetic: Fixed64, fusion: Fixed64) -> CollapseProjection:
    instability = entropy * (Fixed64.one() - magnetic)
    collapse = _clamp01(instability * fusion)
    margin = stability_margin(collapse)
    return CollapseProjection(
        entropy=entropy,
        magnetic=magnetic,
        fusion=fusion,
        instability=instability,
        collapse_probability=collapse,
        stability_margin=margin,
    )
