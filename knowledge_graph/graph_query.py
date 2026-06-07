from __future__ import annotations

from typing import Iterable

from .relation_builder import Relation


def find_relations(relations: Iterable[Relation], source: str | None = None) -> list[Relation]:
    out = []
    for rel in relations:
        if source is None or rel.source == source:
            out.append(rel)
    return out
