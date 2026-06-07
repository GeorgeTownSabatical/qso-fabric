"""Agent wrapper for autonomous hypothesis cycle."""

from __future__ import annotations

from core.orchestrator import _run
from core.service_config import AUTO_REPO, PROPERTY_REPO, REASONING_REPO


class HypothesisAgent:
    def run(self) -> dict:
        return _run(
            [
                "python3",
                "pipeline/autonomous_cycle.py",
                "--graph-json",
                str(PROPERTY_REPO / "data" / "outputs" / "global_graph.json"),
                "--reasoning-dir",
                str(REASONING_REPO / "data" / "outputs"),
                "--output-dir",
                str(AUTO_REPO / "data" / "outputs"),
                "--max-cycles",
                "1",
            ],
            AUTO_REPO,
        )
