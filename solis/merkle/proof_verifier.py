from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MerkleProof:
    leaf_hash: str
    siblings: list[str]
    index: int


def verify_proof(*, proof: MerkleProof, root: str) -> bool:
    if not root:
        return False
    if proof.index < 0:
        return False

    current = proof.leaf_hash
    index = proof.index
    for sibling in proof.siblings:
        if index % 2 == 0:
            combined = current + sibling
        else:
            combined = sibling + current
        current = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        index //= 2
    return current == root


def derive_root_from_hashes(hashes: Iterable[str]) -> str:
    layer = list(hashes)
    if not layer:
        return ""
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layer = [
            hashlib.sha256((layer[i] + layer[i + 1]).encode("utf-8")).hexdigest()
            for i in range(0, len(layer), 2)
        ]
    return layer[0]
