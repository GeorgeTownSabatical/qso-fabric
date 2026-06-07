"""Agent wrapper for graph reasoning service."""

from __future__ import annotations

from core.orchestrator import _run
from core.service_config import PROPERTY_REPO, REASONING_REPO


class ReasoningAgent:
    def run(self) -> dict:
        return _run(
            [
                "python3",
                "pipeline/reasoning_pipeline.py",
                "--graph-json",
                str(PROPERTY_REPO / "data" / "outputs" / "global_graph.json"),
                "--output-dir",
                str(REASONING_REPO / "data" / "outputs"),
            ],
            REASONING_REPO,
        )
