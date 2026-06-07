from __future__ import annotations

from solis.physics.fixed_math import Fixed64


def route_capital(total_capital: Fixed64, allocation: dict[str, Fixed64]) -> dict[str, Fixed64]:
    routed: dict[str, Fixed64] = {}
    for asset in sorted(allocation.keys()):
        routed[asset] = total_capital * allocation[asset]
    return routed
