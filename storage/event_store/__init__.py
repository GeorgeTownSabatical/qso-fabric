from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Protocol

from solis.shared.file_lock import exclusive_path_lock


def _event_dict(event: Any) -> Dict[str, Any]:
    if hasattr(event, "model_dump"):
        payload = dict(event.model_dump(mode="json"))
    elif isinstance(event, dict):
        payload = dict(event)
    else:
        raise TypeError(f"unsupported event type: {type(event)!r}")
    return payload


def _hash_row(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class EventStore(Protocol):
    def append(self, event: Any) -> None: ...

    def query(self, uri: str | None = None, actor: str | None = None, since: datetime | None = None) -> List[Dict[str, Any]]: ...

    def all(self) -> List[Dict[str, Any]]: ...

    def verify_chain(self) -> bool: ...


class InMemoryEventStore:
    def __init__(self) -> None:
        self._rows: List[Dict[str, Any]] = []
        self._lock = RLock()
        self._last_hash = "GENESIS"

    def append(self, event: Any) -> None:
        with self._lock:
            row = _event_dict(event)
            row["prev_hash"] = self._last_hash
            row["hash"] = _hash_row({k: v for k, v in row.items() if k != "hash"})
            self._rows.append(row)
            self._last_hash = str(row["hash"])

    def query(self, uri: str | None = None, actor: str | None = None, since: datetime | None = None) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        with self._lock:
            for row in self._rows:
                if uri is not None and str(row.get("object_uri", "")) != uri:
                    continue
                if actor is not None and str(row.get("actor", "")) != actor:
                    continue
                if since is not None:
                    timestamp_raw = str(row.get("timestamp", ""))
                    try:
                        timestamp = datetime.fromisoformat(timestamp_raw)
                    except ValueError:
                        continue
                    if timestamp < since:
                        continue
                out.append(dict(row))
        return out

    def all(self) -> List[Dict[str, Any]]:
        return self.query()

    def verify_chain(self) -> bool:
        with self._lock:
            prev_hash = "GENESIS"
            for row in self._rows:
                if str(row.get("prev_hash", "")) != prev_hash:
                    return False
                expected = _hash_row({k: v for k, v in row.items() if k != "hash"})
                if str(row.get("hash", "")) != expected:
                    return False
                prev_hash = expected
        return True


class JsonlEventStore:
    """Append-only event log store using newline-delimited JSON."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._lock = RLock()
        with self._lock:
            with exclusive_path_lock(self.path):
                self._last_hash = self._tail_hash_unlocked()

    def append(self, event: Any) -> None:
        row = _event_dict(event)
        with self._lock:
            with exclusive_path_lock(self.path):
                row["prev_hash"] = self._tail_hash_unlocked()
                row["hash"] = _hash_row({k: v for k, v in row.items() if k != "hash"})
                encoded = json.dumps(row, sort_keys=True, separators=(",", ":"))
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(encoded + "\n")
                self._last_hash = str(row["hash"])

    def query(self, uri: str | None = None, actor: str | None = None, since: datetime | None = None) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out: List[Dict[str, Any]] = []
        with self._lock:
            with exclusive_path_lock(self.path):
                with self.path.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        row = json.loads(line)
                        if uri is not None and str(row.get("object_uri", "")) != uri:
                            continue
                        if actor is not None and str(row.get("actor", "")) != actor:
                            continue
                        if since is not None:
                            timestamp_raw = str(row.get("timestamp", ""))
                            try:
                                timestamp = datetime.fromisoformat(timestamp_raw)
                            except ValueError:
                                continue
                            if timestamp < since:
                                continue
                        out.append(row)
        return out

    def all(self) -> List[Dict[str, Any]]:
        return self.query()

    def verify_chain(self) -> bool:
        prev_hash = "GENESIS"
        for row in self.all():
            if str(row.get("prev_hash", "")) != prev_hash:
                return False
            expected = _hash_row({k: v for k, v in row.items() if k != "hash"})
            if str(row.get("hash", "")) != expected:
                return False
            prev_hash = expected
        return True

    def _tail_hash(self) -> str:
        with self._lock:
            with exclusive_path_lock(self.path):
                return self._tail_hash_unlocked()

    def _tail_hash_unlocked(self) -> str:
        if not self.path.exists():
            return "GENESIS"

        last_non_empty = ""
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    last_non_empty = line

        if not last_non_empty:
            return "GENESIS"

        last = json.loads(last_non_empty)
        if isinstance(last, dict):
            raw_hash = last.get("hash")
            if isinstance(raw_hash, str) and raw_hash:
                return raw_hash
            payload = {k: v for k, v in last.items() if k != "hash"}
            payload.setdefault("prev_hash", "GENESIS")
            return _hash_row(payload)
        return "GENESIS"
