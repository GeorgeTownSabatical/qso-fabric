from __future__ import annotations

from typing import Dict, List, Tuple


class GraphState:
    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, str]] = {}
        self.edges: List[Tuple[str, str, float]] = []

    def add_node(self, node_id: str, properties: Dict[str, str]) -> None:
        self.nodes[node_id] = properties

    def add_edge(self, node_a: str, node_b: str, weight: float = 1.0) -> None:
        self.edges.append((node_a, node_b, weight))
