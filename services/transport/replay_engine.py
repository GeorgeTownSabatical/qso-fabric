from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from solis.shared.canonical_json import canonical_json


@dataclass(slots=True)
class TransportReplayResult:
    total_events: int
    modes_seen: list[str]
    hash_chain_ok: bool


class TransportReplayEngine:
    def __init__(self, audit_path: str | Path) -> None:
        self.audit_path = Path(audit_path)

    def replay(self) -> TransportReplayResult:
        if not self.audit_path.exists():
            return TransportReplayResult(total_events=0, modes_seen=[], hash_chain_ok=True)

        modes_seen: list[str] = []
        prev_hash = "GENESIS"
        hash_chain_ok = True
        total = 0

        with self.audit_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                total += 1
                event = json.loads(line)

                if str(event.get("prev_hash", "")) != prev_hash:
                    hash_chain_ok = False

                expected = self._hash({k: v for k, v in event.items() if k != "hash"})
                if str(event.get("hash", "")) != expected:
                    hash_chain_ok = False

                payload = event.get("payload", {})
                if isinstance(payload, dict):
                    mode = payload.get("mode")
                    if isinstance(mode, str) and mode and mode not in modes_seen:
                        modes_seen.append(mode)
                prev_hash = str(event.get("hash", expected))

        return TransportReplayResult(total_events=total, modes_seen=sorted(modes_seen), hash_chain_ok=hash_chain_ok)

    @staticmethod
    def _hash(payload: dict[str, Any]) -> str:
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
