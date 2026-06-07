from __future__ import annotations

from typing import Dict, List, Tuple

from entanglement_graph.entanglement_node import EntanglementNode


class EntanglementGraph:
    def __init__(self) -> None:
        self.nodes: Dict[str, EntanglementNode] = {}

    def entangle(self, uri_a: str, uri_b: str, relationship: str, sync_mode: str = "push") -> None:
        self.nodes.setdefault(uri_a, EntanglementNode(uri_a)).add_link(uri_b, relationship, sync_mode)
        self.nodes.setdefault(uri_b, EntanglementNode(uri_b)).add_link(uri_a, relationship, sync_mode)

    def remove_entanglement(self, uri_a: str, uri_b: str) -> None:
        if uri_a in self.nodes:
            self.nodes[uri_a].remove_link(uri_b)
        if uri_b in self.nodes:
            self.nodes[uri_b].remove_link(uri_a)

    def get_entanglements(self, uri: str) -> List[Tuple[str, str, str]]:
        node = self.nodes.get(uri)
        return [] if not node else node.list_links()
