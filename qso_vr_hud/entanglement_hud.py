from __future__ import annotations

from typing import Any, Dict, List


class EntanglementHUD:
    def __init__(self, graph, controller, visualizer=None) -> None:
        self.graph = graph
        self.controller = controller
        self.visualizer = visualizer
        self.nodes = {}

    def update(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        uris: List[str] = []
        if hasattr(self.graph, "runtime") and hasattr(self.graph.runtime, "registry"):
            uris = list(self.graph.runtime.registry.list_uris())
        elif hasattr(self.graph, "list_resources"):
            uris = list(self.graph.list_resources())

        for uri in uris:
            try:
                links = self.controller.tools.runtime.entanglement.list_links(uri)
            except Exception:
                links = []
            out[uri] = {"link_count": len(links), "links": [link.model_dump(mode="json") for link in links]}
        self.nodes = out
        return {"node_count": len(out), "nodes": out}

    def highlight_node(self, uri, color=(1, 1, 0)) -> None:
        self.nodes.setdefault(uri, {})
        self.nodes[uri]["highlight"] = {"color": list(color)}
