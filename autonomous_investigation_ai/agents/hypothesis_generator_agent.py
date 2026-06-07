"""Hypothesis generator agent wrapper."""

from __future__ import annotations

from core.hypothesis_engine import HypothesisEngine


class HypothesisGeneratorAgent:
    def __init__(self):
        self.engine = HypothesisEngine()

    def generate(self, reasoning_summary: dict, anomalies: dict, clusters: list[dict], influence: list[dict]) -> list[dict]:
        return [h.to_dict() for h in self.engine.generate(reasoning_summary, anomalies, clusters, influence)]
