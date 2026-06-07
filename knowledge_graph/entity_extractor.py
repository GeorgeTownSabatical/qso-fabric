from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Entity:
    node_type: str
    name: str


def extract(text: str) -> list[Entity]:
    # Placeholder extractor; swap with NLP later
    tokens = [t.strip() for t in text.split() if t.strip()]
    return [Entity(node_type="Entity", name=t) for t in tokens[:5]]
