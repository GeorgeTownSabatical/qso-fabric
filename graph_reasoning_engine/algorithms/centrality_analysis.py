"""Centrality and influence scoring."""

from __future__ import annotations

import networkx as nx


def compute_centrality(graph) -> dict[str, dict[str, float]]:
    if graph.number_of_nodes() == 0:
        return {}
    ug = graph.to_undirected()
    pagerank = nx.pagerank(ug)
    between = nx.betweenness_centrality(ug)
    try:
        eigen = nx.eigenvector_centrality(ug, max_iter=500)
    except Exception:
        eigen = {n: 0.0 for n in ug.nodes()}

    out = {}
    for n in ug.nodes():
        out[n] = {
            "pagerank": float(pagerank.get(n, 0.0)),
            "betweenness": float(between.get(n, 0.0)),
            "eigenvector": float(eigen.get(n, 0.0)),
        }
    return out
