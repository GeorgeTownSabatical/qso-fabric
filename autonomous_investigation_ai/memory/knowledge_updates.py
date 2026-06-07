"""Knowledge update stream for confirmed hypotheses."""

from __future__ import annotations

import json
from pathlib import Path


class KnowledgeUpdateStore:
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

    def append(self, update: dict) -> None:
        rows = self._load()
        rows.append(update)
        self.path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
