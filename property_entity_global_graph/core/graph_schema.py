"""Canonical graph schema constants."""

from __future__ import annotations

NODE_TYPES = {
    "Person",
    "Parcel",
    "Trust",
    "LLC",
    "Corporation",
    "Company",
    "Document",
    "CourtCase",
    "SECEntity",
    "Address",
}

EDGE_TYPES = {
    "OWNS",
    "MANAGES",
    "DIRECTOR_OF",
    "TRANSFERRED",
    "REGISTERED_AT",
    "RELATED_TO",
    "OWNED_BY",
    "INVOLVED_IN",
    "OFFICER_OF",
    "SUBSIDIARY_OF",
    "RECORDED_IN",
}
