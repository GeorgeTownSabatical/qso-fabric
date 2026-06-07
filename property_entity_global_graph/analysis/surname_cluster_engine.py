"""Surname cluster analysis across person-like entities."""

from __future__ import annotations

from collections import defaultdict

from core.entity_normalizer import surname


def analyze(graph_store) -> list[dict]:
    graph = graph_store.graph
    clusters = defaultdict(list)
    for node, data in graph.nodes(data=True):
        if data.get("type") not in {"Person", "Trust", "LLC", "Corporation", "Company"}:
            continue
        s = surname(str(node))
        if not s:
            continue
        clusters[s].append(node)

    out = []
    for s, members in clusters.items():
        if len(members) < 2:
            continue
        out.append({"surname": s, "count": len(members), "members": sorted(members)})
    return sorted(out, key=lambda x: x["count"], reverse=True)
