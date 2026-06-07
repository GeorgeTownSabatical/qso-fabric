from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from solis.physics.fixed_math import Fixed64


@dataclass(frozen=True)
class SheafLayer:
    name: str
    field: dict[str, Fixed64]


@dataclass(frozen=True)
class SheafState:
    layers: tuple[SheafLayer, ...]


@dataclass(frozen=True)
class InfluenceMatrix:
    coefficients: dict[str, dict[str, Fixed64]]


def make_sheaf_state(layer_fields: Mapping[str, Mapping[str, Fixed64]]) -> SheafState:
    layers: list[SheafLayer] = []
    for layer_name in sorted(layer_fields.keys()):
        src_field = layer_fields[layer_name]
        field: dict[str, Fixed64] = {}
        for key in sorted(src_field.keys()):
            field[key] = src_field[key]
        layers.append(SheafLayer(name=layer_name, field=field))
    return SheafState(layers=tuple(layers))


def influence_matrix(state: SheafState) -> InfluenceMatrix:
    names = [layer.name for layer in state.layers]
    coeffs: dict[str, dict[str, Fixed64]] = {}

    for source in names:
        coeffs[source] = {}
        for target in names:
            if source == target:
                coeffs[source][target] = Fixed64.one()
            else:
                # Deterministic weak coupling across layers.
                coeffs[source][target] = Fixed64.from_str("0.125")

    return InfluenceMatrix(coefficients=coeffs)


def propagate(state: SheafState, matrix: InfluenceMatrix) -> SheafState:
    result: dict[str, dict[str, Fixed64]] = {layer.name: dict(layer.field) for layer in state.layers}
    layer_lookup = {layer.name: layer for layer in state.layers}

    for target_name in sorted(result.keys()):
        target_field = result[target_name]
        for source_name in sorted(layer_lookup.keys()):
            if source_name == target_name:
                continue
            coefficient = matrix.coefficients.get(source_name, {}).get(target_name, Fixed64.zero())
            source_field = layer_lookup[source_name].field
            for key in sorted(source_field.keys()):
                incoming = source_field[key] * coefficient
                target_field[key] = target_field.get(key, Fixed64.zero()) + incoming

    return make_sheaf_state(result)
