"""APN parsing and normalization utilities."""

from __future__ import annotations

import re


def normalize_apn(apn: str) -> dict[str, str]:
    cleaned = re.sub(r"[^0-9]", "", str(apn or ""))
    if len(cleaned) < 7:
        raise ValueError(f"APN '{apn}' is too short to normalize")
    if len(cleaned) > 9:
        raise ValueError(f"APN '{apn}' is too long to normalize")

    if len(cleaned) == 7:
        cleaned = cleaned[:6] + cleaned[6:].zfill(2)
    if len(cleaned) == 8:
        book = cleaned[0:3]
        page = cleaned[3:6]
        parcel = cleaned[6:8]
    else:  # 9 digits
        book = cleaned[0:3]
        page = cleaned[3:6]
        parcel = cleaned[6:9]

    return {
        "book": book,
        "page": page,
        "parcel": parcel,
        "formatted": f"{book}-{page}-{parcel}",
        "compact": f"{book}{page}{parcel}",
    }
