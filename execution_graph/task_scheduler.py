from __future__ import annotations

from dataclasses import dataclass

from .graph_builder import ExecutionDAG


@dataclass(frozen=True)
class Schedule:
    ordered_steps: tuple[str, ...]


def schedule(dag: ExecutionDAG) -> Schedule:
    return Schedule(ordered_steps=tuple(node.name for node in dag.nodes))
