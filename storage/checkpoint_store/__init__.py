from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Dict, List


def _checkpoint_row(uri: str, event_count: int, hash_chain: str) -> Dict[str, str | int]:
    return {
        "uri": uri,
        "event_count": int(event_count),
        "hash_chain": str(hash_chain),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


class InMemoryCheckpointStore:
    def __init__(self) -> None:
        self._rows: Dict[str, List[Dict[str, str | int]]] = {}
        self._lock = RLock()

    def put(self, uri: str, event_count: int, hash_chain: str) -> Dict[str, str | int]:
        row = _checkpoint_row(uri, event_count, hash_chain)
        with self._lock:
            self._rows.setdefault(uri, []).append(row)
        return dict(row)

    def latest(self, uri: str) -> Dict[str, str | int] | None:
        with self._lock:
            rows = self._rows.get(uri, [])
            return dict(rows[-1]) if rows else None

    def list(self, uri: str) -> List[Dict[str, str | int]]:
        with self._lock:
            return [dict(row) for row in self._rows.get(uri, [])]


class JsonCheckpointStore(InMemoryCheckpointStore):
    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def put(self, uri: str, event_count: int, hash_chain: str) -> Dict[str, str | int]:
        row = super().put(uri, event_count, hash_chain)
        self._save()
        return row

    def _load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, dict) else {}
        for uri, records in rows.items():
            if not isinstance(records, list):
                continue
            self._rows[uri] = [dict(rec) for rec in records if isinstance(rec, dict)]

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._rows, sort_keys=True, indent=2), encoding="utf-8")
