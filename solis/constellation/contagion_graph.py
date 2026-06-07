from __future__ import annotations

from typing import Dict, Iterable


def build_contagion_graph(star_uris: Iterable[str]) -> Dict[str, dict]:
    uris = [str(uri) for uri in star_uris]
    graph: Dict[str, dict] = {}
    for uri in uris:
        graph[uri] = {
            "neighbors": [other for other in uris if other != uri],
            "edge_weight": 1.0 / max(len(uris) - 1, 1),
        }
    return graph
