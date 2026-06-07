"""Document parser adapter for heterogeneous payloads."""

from __future__ import annotations


def parse_recorder_document(doc: dict) -> dict:
    return {
        "document_number": str(doc.get("document_number", "")),
        "recording_date": str(doc.get("recording_date", "")),
        "instrument_type": str(doc.get("instrument_type", "")),
        "apn": str(doc.get("apn", "")),
        "grantor": str(doc.get("grantor", "")),
        "grantee": str(doc.get("grantee", "")),
    }
