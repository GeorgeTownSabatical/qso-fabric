from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from solis.shared.file_lock import exclusive_path_lock


class SandboxOperationStore:
    def __init__(self, root: str | Path = ".codex/state/mcp_qso_edu/sandboxes") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def path_for(self, sandbox_id: str) -> Path:
        normalized = str(sandbox_id).strip()
        if not normalized:
            raise ValueError("sandbox_id must be non-empty")
        return self.root / f"{normalized}.ops.jsonl"

    def read_ops(self, sandbox_id: str) -> list[dict[str, Any]]:
        path = self.path_for(sandbox_id)
        if not path.exists():
            return []
        operations: list[dict[str, Any]] = []
        with self._lock:
            with exclusive_path_lock(path):
                with path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        raw = line.strip()
                        if not raw:
                            continue
                        operations.append(json.loads(raw))
        return operations

    def append_op(self, sandbox_id: str, operation: dict[str, Any]) -> None:
        path = self.path_for(sandbox_id)
        with self._lock:
            with exclusive_path_lock(path):
                payload = dict(operation)
                payload.setdefault("event_id", uuid.uuid4().hex)
                payload.setdefault("ts", datetime.now(timezone.utc).isoformat())
                payload["prev_hash"] = self._tail_hash_unlocked(path)
                payload["hash"] = self._hash_operation(payload)
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")

    def _tail_hash_unlocked(self, path: Path) -> str:
        if not path.exists():
            return "GENESIS"

        last_non_empty = ""
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if raw:
                    last_non_empty = raw

        if not last_non_empty:
            return "GENESIS"

        row = json.loads(last_non_empty)
        raw_hash = str(row.get("hash", ""))
        if raw_hash:
            return raw_hash
        return self._hash_operation(row)

    @staticmethod
    def _hash_operation(operation: dict[str, Any]) -> str:
        payload = {k: v for k, v in operation.items() if k != "hash"}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
