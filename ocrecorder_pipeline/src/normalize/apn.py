"""APN normalization helpers."""

from __future__ import annotations

import re


def normalize_apn(apn: str) -> str:
    raw = str(apn or "").strip().upper()
    if not raw:
        return ""
    digits = re.sub(r"[^0-9]", "", raw)
    if len(digits) == 8:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if len(digits) == 9:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if "-" in raw:
        parts = [p for p in re.split(r"-+", raw) if p]
        if len(parts) >= 3:
            return f"{parts[0]}-{parts[1]}-{parts[2]}"
    return raw
