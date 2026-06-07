"""Community detection algorithms."""

from __future__ import annotations

import networkx as nx


def detect_communities(graph) -> list[set[str]]:
    if graph.number_of_nodes() == 0:
        return []
    ug = graph.to_undirected()
    communities = list(nx.algorithms.community.greedy_modularity_communities(ug))
    return [set(c) for c in communities]


def community_partition(graph) -> dict[str, int]:
    communities = detect_communities(graph)
    out = {}
    for idx, c in enumerate(communities, start=1):
        for node in c:
            out[node] = idx
    return out
