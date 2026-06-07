"""Detect potential shell-company patterns."""

from __future__ import annotations

from collections import defaultdict


def detect(graph_store) -> dict:
    graph = graph_store.graph
    address_to_companies = defaultdict(set)
    director_to_companies = defaultdict(set)

    for u, v, d in graph.edges(data=True):
        rel = d.get("type")
        if rel == "REGISTERED_AT":
            address_to_companies[v].add(u)
        if rel == "DIRECTOR_OF":
            director_to_companies[u].add(v)

    shared_address = [
        {"address": addr, "company_count": len(comps), "companies": sorted(comps)}
        for addr, comps in address_to_companies.items()
        if len(comps) > 1
    ]
    shared_director = [
        {"director": director, "company_count": len(comps), "companies": sorted(comps)}
        for director, comps in director_to_companies.items()
        if len(comps) > 1
    ]
    return {
        "shared_address_clusters": sorted(shared_address, key=lambda x: x["company_count"], reverse=True),
        "shared_director_clusters": sorted(shared_director, key=lambda x: x["company_count"], reverse=True),
    }
