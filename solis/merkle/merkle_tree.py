from __future__ import annotations

import hashlib
from typing import List


def hash_event(event_json: str) -> str:
    return hashlib.sha256(event_json.encode("utf-8")).hexdigest()


def build_merkle_root(hashes: List[str]) -> str:
    if not hashes:
        return ""

    layer = list(hashes)
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])

        layer = [
            hashlib.sha256((layer[i] + layer[i + 1]).encode("utf-8")).hexdigest()
            for i in range(0, len(layer), 2)
        ]

    return layer[0]
