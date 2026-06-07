"""Corporate registry ingestion."""

from __future__ import annotations


def ingest() -> list[dict]:
    return [
        {
            "company_name": "MESNER HOLDINGS LLC",
            "directors": ["Jacob Messer", "J T Messer"],
            "registered_address": "101 Harbor St, Orange, CA",
            "formation_date": "2018-04-01",
        },
        {
            "company_name": "MESSAR VENTURES LLC",
            "directors": ["Jacob T Messer"],
            "registered_address": "101 Harbor Street, Orange, CA",
            "formation_date": "2021-07-20",
        },
    ]
