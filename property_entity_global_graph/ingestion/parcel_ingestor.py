"""Parcel ownership ingestion."""

from __future__ import annotations


def ingest() -> list[dict]:
    return [
        {
            "apn": "405-112-17",
            "owner_name": "JACOB T MESSER",
            "address": "101 Harbor Street, Orange, CA",
            "recorded_date": "2024-01-10",
        },
        {
            "apn": "405-112-18",
            "owner_name": "MESNER HOLDINGS LLC",
            "address": "101 Harbor St, Orange, CA",
            "recorded_date": "2024-01-11",
        },
    ]
