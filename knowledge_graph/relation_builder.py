from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Relation:
    source: str
    relation: str
    target: str


def build_relations(pairs: list[tuple[str, str, str]]) -> list[Relation]:
    return [Relation(*pair) for pair in pairs]
