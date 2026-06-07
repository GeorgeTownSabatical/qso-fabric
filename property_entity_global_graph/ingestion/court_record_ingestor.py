"""Court filing ingestion."""

from __future__ import annotations


def ingest() -> list[dict]:
    return [
        {
            "case_id": "30-2024-01234567-CU-OR-CJC",
            "plaintiff": "Messar Ventures LLC",
            "defendant": "Smith Trust",
            "case_type": "Real Property",
            "filed_date": "2024-10-10",
        }
    ]
