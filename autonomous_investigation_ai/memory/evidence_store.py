"""Persistent evidence ledger."""

from __future__ import annotations

import json
from pathlib import Path


class EvidenceStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        text = self.path.read_text(encoding="utf-8").strip()
        if not text:
            return []
        return json.loads(text)

    def append(self, hypothesis_id: str, evidence_items: list[dict]) -> None:
        rows = self._load()
        for item in evidence_items:
            rows.append({"hypothesis_id": hypothesis_id, **item})
        self.path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
