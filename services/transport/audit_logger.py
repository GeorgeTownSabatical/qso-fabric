from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from services.crypto_access.service import CryptoAccessService
from solis.shared.canonical_json import canonical_json
from solis.shared.file_lock import exclusive_path_lock


class NetworkAuditLogger:
    """Append-only JSONL logger with hash chaining and optional signature."""

    def __init__(self, path: str | Path, crypto: CryptoAccessService | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._lock = RLock()
        self._crypto = crypto
        with self._lock:
            with exclusive_path_lock(self.path):
                self._last_hash = self._tail_hash_unlocked()

    def log(
        self,
        *,
        actor: str,
        object_uri: str,
        payload: Mapping[str, Any],
        kind: str = "transport_event",
        policy_version: str = "v1",
    ) -> dict[str, Any]:
        with self._lock:
            with exclusive_path_lock(self.path):
                event = {
                    "schema_version": "1.0",
                    "event_id": str(uuid.uuid4()),
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "actor": str(actor),
                    "kind": str(kind),
                    "object_uri": str(object_uri),
                    "payload": dict(payload),
                    "policy_version": str(policy_version),
                    "prev_hash": self._tail_hash_unlocked(),
                }
                if self._crypto is not None:
                    event["signature"] = self._crypto.sign(canonical_json({k: v for k, v in event.items() if k != "signature"}))
                event["hash"] = self._hash_event(event)
                encoded = canonical_json(event)
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(encoded + "\n")
                self._last_hash = str(event["hash"])
                return event

    def rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self._lock:
            with exclusive_path_lock(self.path):
                with self.path.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        rows.append(json.loads(line))
        return rows

    def verify_chain(self, *, verify_signature: bool = False) -> bool:
        prev_hash = "GENESIS"
        for row in self.rows():
            if str(row.get("prev_hash", "")) != prev_hash:
                return False
            expected_hash = self._hash_event({k: v for k, v in row.items() if k != "hash"})
            if str(row.get("hash", "")) != expected_hash:
                return False
            if verify_signature and self._crypto is not None:
                signature = str(row.get("signature", ""))
                if not signature:
                    return False
                payload = {k: v for k, v in row.items() if k not in {"signature", "hash"}}
                if not self._crypto.verify(canonical_json(payload), signature):
                    return False
            prev_hash = expected_hash
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

        row = json.loads(last_non_empty)
        stored = str(row.get("hash", ""))
        if stored:
            return stored
        return self._hash_event(row)

    @staticmethod
    def _hash_event(event: Mapping[str, Any]) -> str:
        payload = {k: v for k, v in dict(event).items() if k != "hash"}
        digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        return digest
