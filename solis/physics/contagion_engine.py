from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from solis.physics.fixed_math import Fixed64


@dataclass(frozen=True)
class ExposureEdge:
    source_uri: str
    target_uri: str
    weight: Fixed64


@dataclass(frozen=True)
class ContagionSnapshot:
    exposure_matrix: dict[str, dict[str, Fixed64]]
    collapse_weights: dict[str, Fixed64]
    contagion_index: Fixed64


def exposure_matrix(
    node_uris: list[str],
    *,
    base_weight: Fixed64 | None = None,
) -> dict[str, dict[str, Fixed64]]:
    if not node_uris:
        return {}

    weight = base_weight or Fixed64.from_ratio(1, max(len(node_uris) - 1, 1))
    matrix: dict[str, dict[str, Fixed64]] = {}
    for source in sorted(node_uris):
        matrix[source] = {}
        for target in sorted(node_uris):
            if source == target:
                matrix[source][target] = Fixed64.zero()
            else:
                matrix[source][target] = weight
    return matrix


def contagion_index(
    collapse_by_uri: Mapping[str, Fixed64],
    matrix: Mapping[str, Mapping[str, Fixed64]],
) -> Fixed64:
    if not collapse_by_uri:
        return Fixed64.zero()

    total = Fixed64.zero()
    contributing = 0

    for source in sorted(collapse_by_uri.keys()):
        collapse = collapse_by_uri[source]
        row = matrix.get(source, {})
        row_sum = Fixed64.zero()
        for target in sorted(row.keys()):
            row_sum = row_sum + row[target]

        if row_sum == Fixed64.zero():
            row_sum = Fixed64.one()

        total = total + (collapse * row_sum)
        contributing += 1

    if contributing == 0:
        return Fixed64.zero()

    normalized = total / Fixed64.from_int(contributing)
    return _clamp01(normalized)


def collapse_weight_projection(
    collapse_by_uri: Mapping[str, Fixed64],
    matrix: Mapping[str, Mapping[str, Fixed64]],
) -> dict[str, Fixed64]:
    out: dict[str, Fixed64] = {}
    for source in sorted(collapse_by_uri.keys()):
        collapse = collapse_by_uri[source]
        row = matrix.get(source, {})
        row_sum = Fixed64.zero()
        for target in sorted(row.keys()):
            row_sum = row_sum + row[target]
        if row_sum == Fixed64.zero():
            row_sum = Fixed64.one()
        out[source] = _clamp01(collapse * row_sum)
    return out


def snapshot(collapse_by_uri: Mapping[str, Fixed64]) -> ContagionSnapshot:
    nodes = sorted(collapse_by_uri.keys())
    matrix = exposure_matrix(nodes)
    collapse_weights = collapse_weight_projection(collapse_by_uri, matrix)
    idx = contagion_index(collapse_by_uri, matrix)
    return ContagionSnapshot(
        exposure_matrix=matrix,
        collapse_weights=collapse_weights,
        contagion_index=idx,
    )


def _clamp01(value: Fixed64) -> Fixed64:
    if value < Fixed64.zero():
        return Fixed64.zero()
    if value > Fixed64.one():
        return Fixed64.one()
    return value
