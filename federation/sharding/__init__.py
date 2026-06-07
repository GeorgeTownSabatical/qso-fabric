from __future__ import annotations

import hashlib
from typing import Dict, List


def shard_for_uri(uri: str, shard_count: int) -> int:
    if shard_count <= 0:
        raise ValueError("shard_count must be > 0")
    digest = hashlib.sha256(uri.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % shard_count


def shard_uris(uris: List[str], shard_count: int) -> Dict[int, List[str]]:
    out: Dict[int, List[str]] = {idx: [] for idx in range(shard_count)}
    for uri in sorted(uris):
        out[shard_for_uri(uri, shard_count)].append(uri)
    return out
