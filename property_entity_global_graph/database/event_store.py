"""Append-only event ledger."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


class EventStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return "GENESIS"
        last = self.path.read_text(encoding="utf-8").strip().splitlines()[-1]
        return json.loads(last).get("hash", "GENESIS")

    def append(self, kind: str, payload: dict) -> dict:
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "payload": payload,
            "prev_hash": self._last_hash(),
        }
        raw = json.dumps(event, sort_keys=True, separators=(",", ":"))
        event["hash"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event
