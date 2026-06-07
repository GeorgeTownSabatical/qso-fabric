from __future__ import annotations

from dataclasses import dataclass

from solis.physics.fixed_math import Fixed64


@dataclass(frozen=True)
class RevenueSplit:
    creator: Fixed64
    operator: Fixed64
    protocol: Fixed64


def split_revenue(total: Fixed64, ratio_creator: Fixed64, ratio_operator: Fixed64, ratio_protocol: Fixed64) -> RevenueSplit:
    allocated = ratio_creator + ratio_operator + ratio_protocol
    if allocated != Fixed64.one():
        raise ValueError("revenue ratio must sum to 1.0")

    return RevenueSplit(
        creator=total * ratio_creator,
        operator=total * ratio_operator,
        protocol=total * ratio_protocol,
    )
