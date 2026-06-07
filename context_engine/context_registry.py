from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class ContextObject:
    id: str
    entities: tuple[str, ...] = field(default_factory=tuple)
    relations: tuple[str, ...] = field(default_factory=tuple)
    documents: tuple[str, ...] = field(default_factory=tuple)
    equations: tuple[str, ...] = field(default_factory=tuple)

    def merge(self, other: "ContextObject") -> "ContextObject":
        if self.id != other.id:
            raise ValueError("ContextObject id mismatch")
        return ContextObject(
            id=self.id,
            entities=_uniq(self.entities + other.entities),
            relations=_uniq(self.relations + other.relations),
            documents=_uniq(self.documents + other.documents),
            equations=_uniq(self.equations + other.equations),
        )


def _uniq(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return tuple(out)
