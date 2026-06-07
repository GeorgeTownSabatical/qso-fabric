from __future__ import annotations

from dataclasses import dataclass

from .graph_builder import ExecutionDAG


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    steps: tuple[str, ...]


def execute(dag: ExecutionDAG) -> ExecutionResult:
    steps = tuple(node.name for node in dag.nodes)
    return ExecutionResult(status="ok", steps=steps)
