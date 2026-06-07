from __future__ import annotations

import json
from typing import Any


def canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization used for hashing and replay checks."""

    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def canonical_loads(text: str) -> Any:
    return json.loads(text)
