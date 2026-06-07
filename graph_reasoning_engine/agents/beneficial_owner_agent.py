"""Beneficial owner tracing agent."""

from __future__ import annotations

import networkx as nx


class BeneficialOwnerAgent:
    def run(self, graph, max_depth: int = 5) -> list[dict]:
        people = [n for n, d in graph.nodes(data=True) if d.get("type") == "Person"]
        parcels = [n for n, d in graph.nodes(data=True) if d.get("type") == "Parcel"]
        out = []
        ug = graph.to_undirected()
        for person in people:
            assets = []
            for parcel in parcels:
                try:
                    path = nx.shortest_path(ug, source=person, target=parcel)
                except Exception:
                    continue
                depth = len(path) - 1
                if depth <= max_depth:
                    assets.append({"parcel": parcel, "depth": depth, "path": path})
            if assets:
                confidence = min(1.0, 0.45 + 0.1 * len(assets))
                out.append({"entity": person, "assets_controlled": assets, "confidence": round(confidence, 4)})
        out.sort(key=lambda x: (x["confidence"], len(x["assets_controlled"])), reverse=True)
        return out
