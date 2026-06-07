"""Graph neighborhood expansion for investigation pivots."""

from __future__ import annotations

from collections import deque


def expand_network(graph_store, seed_node: str, depth: int = 2) -> dict:
    graph = graph_store.graph
    if seed_node not in graph:
        return {"seed": seed_node, "visited": [], "depth": depth}

    visited = {seed_node}
    queue = deque([(seed_node, 0)])
    while queue:
        node, lvl = queue.popleft()
        if lvl >= depth:
            continue
        for nbr in graph.neighbors(node):
            if nbr in visited:
                continue
            visited.add(nbr)
            queue.append((nbr, lvl + 1))
    return {"seed": seed_node, "visited": sorted(visited), "depth": depth}
