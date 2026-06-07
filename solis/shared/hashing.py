from __future__ import annotations

import hashlib
from typing import Any

from solis.shared.canonical_json import canonical_json


def sha256_hex_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_hex_obj(obj: Any) -> str:
    return sha256_hex_text(canonical_json(obj))
