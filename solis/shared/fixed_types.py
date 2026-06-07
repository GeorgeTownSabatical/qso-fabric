from __future__ import annotations

from typing import Iterable, TypeAlias

from solis.physics.fixed_math import Fixed64

FixedLike: TypeAlias = Fixed64 | int | str


def to_fixed(value: FixedLike) -> Fixed64:
    if isinstance(value, Fixed64):
        return value
    if isinstance(value, int):
        return Fixed64.from_int(value)
    if isinstance(value, str):
        return Fixed64.from_str(value)
    raise TypeError(f"unsupported fixed value: {type(value)!r}")


def sum_fixed(values: Iterable[FixedLike]) -> Fixed64:
    total = Fixed64.zero()
    for value in values:
        total = total + to_fixed(value)
    return total
