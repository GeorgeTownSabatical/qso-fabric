from __future__ import annotations

from solis.agent.dsl.ast import AgentAST
from solis.agent.dsl.parser import parse_agent_dsl
from solis.agent.runtime.execution_graph import ExecutionGraph, GraphNode
from solis.shared.hashing import sha256_hex_obj


def compile_to_graph(ast: AgentAST) -> tuple[ExecutionGraph, str]:
    nodes: list[GraphNode] = []
    edges: list[tuple[str, str]] = []

    nodes.append(GraphNode(node_id="start", op="start", payload={"agent": ast.name, "version": ast.version}))

    prev = "start"
    for idx, alloc in enumerate(ast.allocation, start=1):
        node_id = f"alloc_{idx:03d}"
        nodes.append(GraphNode(node_id=node_id, op="allocate", payload={"asset": alloc.asset, "percent": alloc.percent}))
        edges.append((prev, node_id))
        prev = node_id

    risk_id = "risk_guard"
    nodes.append(
        GraphNode(
            node_id=risk_id,
            op="risk_guard",
            payload={
                "max_drawdown": ast.risk.max_drawdown,
                "collapse_threshold": ast.risk.collapse_threshold,
                "no_margin": str(ast.risk.no_margin).lower(),
            },
        )
    )
    edges.append((prev, risk_id))

    end_id = "end"
    nodes.append(GraphNode(node_id=end_id, op="end", payload={"rebalance_interval": ast.rebalance_interval}))
    edges.append((risk_id, end_id))

    graph = ExecutionGraph(nodes=tuple(nodes), edges=tuple(edges))
    graph_hash = sha256_hex_obj(
        {
            "nodes": [
                {
                    "node_id": n.node_id,
                    "op": n.op,
                    "payload": dict(sorted(n.payload.items())),
                }
                for n in graph.nodes
            ],
            "edges": list(graph.edges),
        }
    )
    return graph, graph_hash


def compile_dsl(text: str) -> tuple[ExecutionGraph, str]:
    ast = parse_agent_dsl(text)
    return compile_to_graph(ast)
