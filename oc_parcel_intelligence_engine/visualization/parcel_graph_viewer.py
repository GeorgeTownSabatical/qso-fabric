"""Parcel graph visualization (optional matplotlib)."""

from __future__ import annotations

import networkx as nx


def show_graph(graph: nx.MultiDiGraph) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required for visualization") from exc

    pos = nx.spring_layout(graph, seed=42)
    nx.draw_networkx(graph, pos=pos, with_labels=True, node_size=1000, font_size=8)
    plt.title("Parcel Ownership Graph")
    plt.tight_layout()
    plt.show()
