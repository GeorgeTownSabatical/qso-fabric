"""Task payload helper for reasoning jobs."""

from __future__ import annotations


def build_task_payload() -> dict:
    return {"job": "run_reasoning", "algorithms": ["community_detection", "centrality_analysis", "link_prediction", "anomaly_detection"]}
