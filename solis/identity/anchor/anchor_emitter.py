from __future__ import annotations

from dataclasses import dataclass, field

from solis.identity.anchor.merkle import hash_leaf, merkle_root
from solis.services.qso_bridge import QSOBridge


@dataclass
class AnchorEmitter:
    qso: QSOBridge
    epoch_size: int = 10_000
    leaves: list[str] = field(default_factory=list)

    def append_event(self, canonical_event_json: str) -> None:
        self.leaves.append(hash_leaf(canonical_event_json))

    def should_anchor(self) -> bool:
        return len(self.leaves) > 0 and len(self.leaves) % self.epoch_size == 0

    def emit_if_ready(self, *, actor: str = "identity.anchor") -> dict[str, str] | None:
        if not self.should_anchor():
            return None

        epoch = len(self.leaves) // self.epoch_size
        root = merkle_root(self.leaves)
        signature = self.qso.sign(root)
        uri = f"qso://solis.anchor.{epoch}"

        if not self.qso.has(uri):
            self.qso.create(uri, {"type": "identity_anchor"})

        self.qso.patch(
            uri,
            {
                "epoch": epoch,
                "root": root,
                "signature": signature,
                "leaf_count": len(self.leaves),
            },
            actor=actor,
            policy_version="v1",
            node_id="identity-anchor",
        )
        return {"uri": uri, "root": root, "signature": signature}
