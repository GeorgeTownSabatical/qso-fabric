"""Recorder document ingestion."""

from __future__ import annotations


def ingest() -> list[dict]:
    return [
        {
            "document_number": "2024000012345",
            "recording_date": "2024-02-12",
            "instrument_type": "Grant Deed",
            "apn": "405-112-17",
            "grantor": "Smith Trust",
            "grantee": "Jacob Messer",
        },
        {
            "document_number": "2024000012399",
            "recording_date": "2024-06-02",
            "instrument_type": "Quitclaim Deed",
            "apn": "405-112-17",
            "grantor": "Jacob T Messer",
            "grantee": "Mesner Holdings LLC",
        },
        {
            "document_number": "2024000012550",
            "recording_date": "2024-08-21",
            "instrument_type": "Grant Deed",
            "apn": "405-112-18",
            "grantor": "Mesner Holdings LLC",
            "grantee": "Messar Ventures LLC",
        },
    ]
