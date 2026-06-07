"""Agent wrapper for ingestion service."""

from __future__ import annotations

from core.orchestrator import _run
from core.service_config import PROPERTY_REPO


class IngestionAgent:
    def run(self) -> dict:
        return _run(["python3", "run_global_graph.py"], PROPERTY_REPO)
