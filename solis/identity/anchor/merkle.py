from __future__ import annotations

import hashlib


def hash_leaf(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return ""

    layer = list(leaves)
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layer = [
            hashlib.sha256((layer[i] + layer[i + 1]).encode("utf-8")).hexdigest()
            for i in range(0, len(layer), 2)
        ]
    return layer[0]
