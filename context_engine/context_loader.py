from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

from .cluster_router import normalize_cluster_id
from .context_registry import ContextObject

MEMORY_INDEX = Path(__file__).with_name("memory_index.json")


def load_context(cluster_id: str | Sequence[str]) -> ContextObject | dict[str, ContextObject]:
    data = _load_index()
    if isinstance(cluster_id, str):
        normalized = normalize_cluster_id(cluster_id)
        return _context_from_cluster(normalized, data)

    clusters = [normalize_cluster_id(c) for c in cluster_id]
    merged = _merge_contexts([_context_from_cluster(c, data) for c in clusters])
    return {"merged": merged, "clusters": {c: _context_from_cluster(c, data) for c in clusters}}


def _load_index() -> dict:
    return json.loads(MEMORY_INDEX.read_text(encoding="utf-8"))


def _context_from_cluster(cluster_id: str, data: dict) -> ContextObject:
    cluster = data.get("clusters", {}).get(cluster_id, {})
    return ContextObject(
        id=cluster_id,
        entities=tuple(cluster.get("entities", [])),
        relations=tuple(cluster.get("relations", [])),
        documents=tuple(cluster.get("documents", [])),
        equations=tuple(cluster.get("equations", [])),
    )


def _merge_contexts(contexts: Iterable[ContextObject]) -> ContextObject:
    merged = ContextObject(id="MERGED")
    for ctx in contexts:
        merged = ContextObject(
            id=merged.id,
            entities=tuple(dict.fromkeys(merged.entities + ctx.entities)),
            relations=tuple(dict.fromkeys(merged.relations + ctx.relations)),
            documents=tuple(dict.fromkeys(merged.documents + ctx.documents)),
            equations=tuple(dict.fromkeys(merged.equations + ctx.equations)),
        )
    return merged
