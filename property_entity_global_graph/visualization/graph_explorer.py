"""Graph explorer export helpers."""

from __future__ import annotations

from pathlib import Path


def export_html(graph_store, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from pyvis.network import Network
    except Exception:
        data = {
            "node_count": graph_store.graph.number_of_nodes(),
            "edge_count": graph_store.graph.number_of_edges(),
            "message": "pyvis not installed; wrote summary only",
        }
        path.write_text(str(data), encoding="utf-8")
        return path

    net = Network(height="900px", width="100%", directed=True)
    for node, attrs in graph_store.graph.nodes(data=True):
        net.add_node(node, label=str(node), title=str(attrs), group=attrs.get("type", "Entity"))
    for u, v, attrs in graph_store.graph.edges(data=True):
        net.add_edge(u, v, title=attrs.get("type", "RELATED"), label=attrs.get("type", "RELATED"))
    net.save_graph(str(path))
    return path
