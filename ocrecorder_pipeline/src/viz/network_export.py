"""Graph export helpers."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd


def export_graphml(graph: nx.Graph, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, path)
    return path


def export_edge_table(graph: nx.Graph, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"source": u, "target": v} for u, v in graph.edges()]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path
