"""Anomaly detection agent."""

from __future__ import annotations

from algorithms.anomaly_detection import detect_anomalies


class AnomalyAgent:
    def run(self, graph) -> dict:
        return detect_anomalies(graph)
