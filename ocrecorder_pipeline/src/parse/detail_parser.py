"""Optional detail-page parsing helpers."""

from __future__ import annotations


def parse_detail_fields(html: str) -> dict:
    """Return a conservative detail payload.

    This placeholder avoids hard-coding brittle selectors until live-page selectors
    are pinned for the current RecorderWorks markup.
    """
    return {
        "legal_description": None,
        "addresses": [],
        "notaries": [],
        "notes": "detail parser placeholder; add concrete selectors per current site markup",
        "html_size": len(html),
    }
