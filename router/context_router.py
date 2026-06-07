from __future__ import annotations

from typing import Iterable

from .resolution_engine import ExecutionPlan, resolve


def route(context_key: str, modules: Iterable[str]) -> ExecutionPlan:
    return resolve(context_key, modules)
