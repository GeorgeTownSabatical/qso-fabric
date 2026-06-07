"""Detect beneficial ownership chains in graph paths."""

from __future__ import annotations


def detect(graph_store, max_depth: int = 6) -> list[dict]:
    graph = graph_store.graph
    parcels = [n for n, d in graph.nodes(data=True) if d.get("type") == "Parcel"]
    people = [n for n, d in graph.nodes(data=True) if d.get("type") == "Person"]

    findings = []
    ug = graph.to_undirected()
    for parcel in parcels:
        best = None
        for person in people:
            if person == parcel:
                continue
            try:
                path = next(iter(__import__("networkx").all_simple_paths(ug, source=person, target=parcel, cutoff=max_depth)))
            except Exception:
                continue
            depth = len(path) - 1
            if best is None or depth < best["chain_depth"]:
                best = {
                    "beneficial_owner": person,
                    "asset": parcel,
                    "chain_depth": depth,
                    "path": path,
                }
        if best:
            findings.append(best)
    return findings
