from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    op: str
    payload: dict[str, str]


@dataclass(frozen=True)
class ExecutionGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[tuple[str, str], ...]
