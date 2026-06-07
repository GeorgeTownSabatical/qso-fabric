from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .module_registry import MODULES


@dataclass(frozen=True)
class ExecutionPlan:
    contexts: tuple[str, ...]
    modules: tuple[str, ...]
    agent_roles: tuple[str, ...]
    execution_graph: tuple[str, ...]


def resolve(context_key: str, modules: Iterable[str]) -> ExecutionPlan:
    meta = MODULES.get(context_key, {})
    contexts = tuple(meta.get("contexts", []))
    selected = tuple(modules)
    agent_roles = _default_roles(selected)
    execution_graph = _default_graph(selected)
    return ExecutionPlan(
        contexts=contexts,
        modules=selected,
        agent_roles=agent_roles,
        execution_graph=execution_graph,
    )


def _default_roles(modules: Iterable[str]) -> tuple[str, ...]:
    if not modules:
        return ("planner",)
    return ("theorist", "programmer", "verifier")


def _default_graph(modules: Iterable[str]) -> tuple[str, ...]:
    return ("LoadContext", "ResolveModules", "Execute", "Summarize")
