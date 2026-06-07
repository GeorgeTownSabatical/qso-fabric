from __future__ import annotations

from solis.physics.collapse_engine import (
    collapse_drift,
    collapse_probability_v1,
    project_collapse,
    stability_margin,
)
from solis.physics.entropy_engine import entropy_delta, entropy_gradient, entropy_projection
from solis.physics.fixed_math import Fixed64
from solis.shared.hashing import sha256_hex_obj


def test_collapse_engine_is_deterministic_and_bounded() -> None:
    entropy = Fixed64.from_str("0.3")
    magnetic = Fixed64.from_str("0.8")
    fusion = Fixed64.from_str("0.9")

    first = project_collapse(entropy, magnetic, fusion)
    second = project_collapse(entropy, magnetic, fusion)

    assert first == second
    assert first.collapse_probability >= Fixed64.zero()
    assert first.collapse_probability <= Fixed64.one()
    assert sha256_hex_obj({"collapse": first.collapse_probability.to_raw()}) == sha256_hex_obj(
        {"collapse": second.collapse_probability.to_raw()}
    )


def test_collapse_helpers() -> None:
    low = collapse_probability_v1(Fixed64.from_str("0.1"), Fixed64.from_str("0.9"), Fixed64.from_str("0.5"))
    high = collapse_probability_v1(Fixed64.from_str("2.0"), Fixed64.from_str("-1.0"), Fixed64.from_str("3.0"))

    assert low < high
    assert high == Fixed64.one()
    assert stability_margin(high) == Fixed64.zero()
    assert collapse_drift(low, high) == high - low


def test_entropy_engine_deterministic_projection() -> None:
    prev = Fixed64.from_str("0.10")
    curr = Fixed64.from_str("0.16")

    d = entropy_delta(prev, curr)
    g = entropy_gradient(prev, curr, steps=3)
    projected = entropy_projection(curr, Fixed64.from_str("-0.20"))

    assert d == Fixed64.from_str("0.06")
    assert g == Fixed64.from_str("0.02")
    assert projected == Fixed64.zero()
