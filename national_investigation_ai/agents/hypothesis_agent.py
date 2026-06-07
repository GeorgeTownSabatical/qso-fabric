"""Task payload helper for hypothesis jobs."""

from __future__ import annotations


def build_task_payload() -> dict:
    return {"job": "run_hypothesis_cycle", "mode": "autonomous"}
