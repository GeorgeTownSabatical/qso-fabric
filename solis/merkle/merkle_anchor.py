from __future__ import annotations

from solis.merkle.merkle_tree import build_merkle_root, hash_event


class StellarMerkleAnchor:
    def __init__(self, epoch_size: int = 10_000) -> None:
        if epoch_size <= 0:
            raise ValueError("epoch_size must be > 0")
        self.epoch_size = epoch_size
        self.event_hashes: list[str] = []

    def append_event(self, event_json: str) -> None:
        self.event_hashes.append(hash_event(event_json))

    def root(self) -> str:
        return build_merkle_root(self.event_hashes)

    def should_anchor(self) -> bool:
        return len(self.event_hashes) > 0 and len(self.event_hashes) % self.epoch_size == 0

    def epoch(self) -> int:
        if not self.event_hashes:
            return 0
        return len(self.event_hashes) // self.epoch_size
