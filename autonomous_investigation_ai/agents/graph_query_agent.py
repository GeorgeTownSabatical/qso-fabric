"""Graph query agent for local graph artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx


class GraphQueryAgent:
    def __init__(self, graph_json_path: Path):
        payload = json.loads(graph_json_path.read_text(encoding="utf-8"))
        self.graph = nx.MultiDiGraph()
        for n in payload.get("nodes", []):
            node_id = n["id"]
            attrs = {k: v for k, v in n.items() if k != "id"}
            self.graph.add_node(node_id, **attrs)
        for e in payload.get("edges", []):
            attrs = {k: v for k, v in e.items() if k not in {"source", "target"}}
            self.graph.add_edge(e["source"], e["target"], **attrs)

    def shared_address_clusters(self, threshold: int = 2) -> list[dict]:
        by_address = {}
        for u, v, d in self.graph.edges(data=True):
            if d.get("type") != "REGISTERED_AT":
                continue
            by_address.setdefault(v, set()).add(u)
        return [
            {"address": addr, "entities": sorted(list(entities)), "count": len(entities)}
            for addr, entities in by_address.items()
            if len(entities) >= threshold
        ]

    def trace_entity_assets(self, entity_name: str, max_depth: int = 5) -> list[str]:
        parcels = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "Parcel"]
        ug = self.graph.to_undirected()
        assets = []
        if entity_name not in ug:
            return assets
        for parcel in parcels:
            try:
                path = nx.shortest_path(ug, source=entity_name, target=parcel)
            except Exception:
                continue
            if len(path) - 1 <= max_depth:
                assets.append(parcel)
        return sorted(set(assets))
