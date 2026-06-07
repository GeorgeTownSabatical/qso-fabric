from __future__ import annotations

import pytest

from solis.physics.fixed_math import RAW_MAX, Fixed64, FixedOverflowError
from solis.shared.hashing import sha256_hex_obj


def _run_sequence() -> dict[str, int]:
    a = Fixed64.from_str("1.2500")
    b = Fixed64.from_str("2.7500")
    c = Fixed64.from_ratio(7, 10)

    out = {
        "sum": (a + b).to_raw(),
        "diff": (b - c).to_raw(),
        "mul": (a * c).to_raw(),
        "div": (b / a).to_raw(),
        "chain": (((a + b) * c) / Fixed64.from_int(2)).to_raw(),
    }
    return out


def test_fixed64_deterministic_sequence_hash() -> None:
    first = _run_sequence()
    second = _run_sequence()

    assert first == second
    assert sha256_hex_obj(first) == sha256_hex_obj(second)


def test_fixed64_parse_and_render_are_stable() -> None:
    v = Fixed64.from_str("123.456789")
    assert v.to_str(6) == "123.456789"

    w = Fixed64.from_str("-0.125")
    assert (w * Fixed64.from_int(8)).to_int_floor() == -1

    sci = Fixed64.from_str("1.6e-17")
    assert sci.to_raw() >= 0
    assert sci.to_str(18).startswith("0.")


def test_fixed64_rejects_float_operands() -> None:
    with pytest.raises(TypeError):
        _ = Fixed64.from_int(1.2)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        _ = Fixed64.from_int(1) + 1.2  # type: ignore[operator]


def test_fixed64_overflow_detection() -> None:
    near_max = Fixed64.from_raw(RAW_MAX)
    with pytest.raises(FixedOverflowError):
        _ = near_max + Fixed64.one()
