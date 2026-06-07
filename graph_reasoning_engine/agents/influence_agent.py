"""Influence analysis agent."""

from __future__ import annotations

from algorithms.centrality_analysis import compute_centrality


class InfluenceAgent:
    def run(self, graph, top_k: int = 20) -> list[dict]:
        centrality = compute_centrality(graph)
        rows = []
        for node, scores in centrality.items():
            rows.append({"node": node, **scores, "score": scores["pagerank"] + scores["betweenness"] + scores["eigenvector"]})
        rows.sort(key=lambda x: x["score"], reverse=True)
        return rows[:top_k]
