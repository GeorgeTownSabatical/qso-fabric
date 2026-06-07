from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    name: str


@dataclass(frozen=True)
class ExecutionDAG:
    nodes: tuple[Node, ...]


def build(command: str) -> ExecutionDAG:
    # Minimal deterministic DAG scaffold
    nodes = (
        Node("LoadContext"),
        Node("GenerateEquations"),
        Node("BuildSimulation"),
        Node("RunSimulation"),
        Node("OutputResults"),
    )
    return ExecutionDAG(nodes=nodes)
