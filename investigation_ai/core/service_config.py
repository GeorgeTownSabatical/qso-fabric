"""Path and service config for local control node."""

from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PROPERTY_REPO = BASE / "property_entity_global_graph"
REASONING_REPO = BASE / "graph_reasoning_engine"
AUTO_REPO = BASE / "autonomous_investigation_ai"
OUT = Path(__file__).resolve().parents[1] / "data" / "outputs"
