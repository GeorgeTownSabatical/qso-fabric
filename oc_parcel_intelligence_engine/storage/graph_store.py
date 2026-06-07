"""Graph storage helpers."""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from storage.json_store import save_json


def save_graph_json(graph, path: Path) -> Path:
    return save_json(path, graph.to_dict())


def save_graphml(nx_graph: nx.MultiDiGraph, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(nx_graph, path)
    return path
