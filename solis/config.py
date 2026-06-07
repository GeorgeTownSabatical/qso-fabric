from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolisConfig:
    """Deterministic runtime configuration for Solis services."""

    policy_version: str = "v1"
    node_id: str = "solis"
    anchor_interval: int = 10_000
    collapse_warning_threshold: float = 0.72
    cascade_threshold: float = 0.78
    signal_window: int = 5
    runtime_gate_enabled: bool = True
    runtime_gate_nodes: tuple[str, ...] = ("node-a", "node-b", "node-c")
    require_zk_proof: bool = False


SPHERECHAIN_STAR_URI = "qso://solis.star.spherechain"
