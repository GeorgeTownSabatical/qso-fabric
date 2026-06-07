from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Dict, List


class InMemorySnapshotStore:
    def __init__(self) -> None:
        self._blobs: Dict[str, Dict[str, bytes]] = {}
        self._lock = RLock()

    def put(self, uri: str, blob: bytes, label: str | None = None) -> str:
        tag = label or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        with self._lock:
            self._blobs.setdefault(uri, {})[tag] = bytes(blob)
        return tag

    def get(self, uri: str, label: str) -> bytes:
        with self._lock:
            rows = self._blobs.get(uri, {})
            if label not in rows:
                raise KeyError(f"snapshot not found: {uri}@{label}")
            return bytes(rows[label])

    def list(self, uri: str) -> List[str]:
        with self._lock:
            return sorted(self._blobs.get(uri, {}))


class FileSnapshotStore(InMemorySnapshotStore):
    def __init__(self, root: str | Path) -> None:
        super().__init__()
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._index_path = self.root / "index.json"
        self._index: Dict[str, List[str]] = {}
        self._load_index()

    def put(self, uri: str, blob: bytes, label: str | None = None) -> str:
        tag = super().put(uri, blob, label=label)
        uri_slug = base64.urlsafe_b64encode(uri.encode("utf-8")).decode("ascii").rstrip("=")
        target_dir = self.root / uri_slug
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{tag}.qff"
        target_path.write_bytes(blob)
        self._index.setdefault(uri, [])
        if tag not in self._index[uri]:
            self._index[uri].append(tag)
            self._index[uri].sort()
            self._save_index()
        return tag

    def get(self, uri: str, label: str) -> bytes:
        uri_slug = base64.urlsafe_b64encode(uri.encode("utf-8")).decode("ascii").rstrip("=")
        target_path = self.root / uri_slug / f"{label}.qff"
        if target_path.exists():
            return target_path.read_bytes()
        return super().get(uri, label)

    def list(self, uri: str) -> List[str]:
        labels = sorted(self._index.get(uri, []))
        if labels:
            return labels
        return super().list(uri)

    def _load_index(self) -> None:
        if not self._index_path.exists():
            return
        data = json.loads(self._index_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return
        for uri, labels in data.items():
            if not isinstance(labels, list):
                continue
            self._index[uri] = sorted(str(label) for label in labels)

    def _save_index(self) -> None:
        self._index_path.write_text(json.dumps(self._index, sort_keys=True, indent=2), encoding="utf-8")
