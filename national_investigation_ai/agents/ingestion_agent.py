"""Task publishing helper for ingestion jobs."""

from __future__ import annotations


def build_task_payload() -> dict:
    return {"job": "run_ingestion", "scope": "county_batch"}
