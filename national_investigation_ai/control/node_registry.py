"""Worker node registry."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


class NodeRegistry:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        text = self.path.read_text(encoding="utf-8").strip()
        return json.loads(text) if text else []

    def _save(self, rows: list[dict]) -> None:
        self.path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def register(self, node_id: str, role: str) -> dict:
        rows = self._load()
        now = datetime.now(timezone.utc).isoformat()
        row = {"node_id": node_id, "role": role, "registered_at": now, "last_seen": now}
        rows = [r for r in rows if r.get("node_id") != node_id]
        rows.append(row)
        self._save(rows)
        return row

    def heartbeat(self, node_id: str) -> None:
        rows = self._load()
        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            if row.get("node_id") == node_id:
                row["last_seen"] = now
        self._save(rows)

    def list_nodes(self) -> list[dict]:
        return self._load()
