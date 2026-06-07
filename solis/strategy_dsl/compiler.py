from __future__ import annotations

from solis.agent.dsl.ast import AgentAST
from solis.agent.dsl.compiler import compile_dsl, compile_to_graph
from solis.agent.dsl.parser import parse_agent_dsl
from solis.agent.runtime.execution_graph import ExecutionGraph


def parse_strategy_dsl(text: str) -> AgentAST:
    return parse_agent_dsl(text)


def compile_strategy_ast(ast: AgentAST) -> tuple[ExecutionGraph, str]:
    return compile_to_graph(ast)


def compile_strategy_dsl(text: str) -> tuple[ExecutionGraph, str]:
    return compile_dsl(text)
