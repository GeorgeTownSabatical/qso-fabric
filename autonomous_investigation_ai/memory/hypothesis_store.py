"""Persistent hypothesis ledger."""

from __future__ import annotations

import json
from pathlib import Path


class HypothesisStore:
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

    def _save(self, rows: list[dict]) -> None:
        self.path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def upsert(self, hypothesis: dict) -> None:
        rows = self._load()
        hid = hypothesis.get("hypothesis_id")
        replaced = False
        for i, row in enumerate(rows):
            if row.get("hypothesis_id") == hid:
                rows[i] = hypothesis
                replaced = True
                break
        if not replaced:
            rows.append(hypothesis)
        self._save(rows)
