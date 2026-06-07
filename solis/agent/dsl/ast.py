from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationRule:
    asset: str
    percent: str


@dataclass(frozen=True)
class RiskConfig:
    max_drawdown: str
    collapse_threshold: str
    no_margin: bool


@dataclass(frozen=True)
class AgentAST:
    name: str
    version: str
    assets: tuple[str, ...]
    allocation: tuple[AllocationRule, ...]
    rebalance_interval: str
    risk: RiskConfig
