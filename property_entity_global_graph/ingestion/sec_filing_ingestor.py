"""SEC-like filing ingestion."""

from __future__ import annotations


def ingest() -> list[dict]:
    return [
        {
            "company": "MESNER HOLDINGS LLC",
            "officers": ["Jacob Messer"],
            "subsidiaries": ["Messar Ventures LLC"],
            "address": "101 Harbor St, Orange, CA",
            "filing_date": "2024-09-01",
        }
    ]
