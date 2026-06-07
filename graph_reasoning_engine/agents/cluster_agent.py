"""Cluster reasoning agent."""

from __future__ import annotations

from algorithms.community_detection import detect_communities


class ClusterAgent:
    def run(self, graph) -> list[dict]:
        communities = detect_communities(graph)
        out = []
        for i, members in enumerate(communities, start=1):
            out.append({"cluster_id": i, "size": len(members), "members": sorted(members)})
        return out
