from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from solis.shared.file_lock import exclusive_path_lock


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationBridge:
    def __init__(self, path: str | Path = ".codex/state/plus_bridge.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._lock = Lock()
        self._last_seq = 0
        self._last_hash = "GENESIS"
        self._bootstrap_tail()

    def append(
        self,
        *,
        source: str,
        content: str,
        session_id: str = "shared",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_source = str(source).strip()
        normalized_content = str(content).strip()
        if not normalized_source:
            raise ValueError("source must be non-empty")
        if not normalized_content:
            raise ValueError("content must be non-empty")

        with self._lock:
            with exclusive_path_lock(self.path):
                tail_seq, tail_hash = self._tail_state_unlocked()
                payload = {
                    "schema_version": "1.0",
                    "event_id": uuid.uuid4().hex,
                    "seq": tail_seq + 1,
                    "ts": _utc_now(),
                    "session_id": str(session_id).strip() or "shared",
                    "source": normalized_source,
                    "content": normalized_content,
                    "metadata": metadata or {},
                    "prev_hash": tail_hash,
                }
                payload["hash"] = self._hash_payload(payload)

                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")

                self._last_seq = int(payload["seq"])
                self._last_hash = str(payload["hash"])
                return dict(payload)

    def read(self, *, after_seq: int = 0, limit: int = 200) -> dict[str, Any]:
        bounded_after = max(0, int(after_seq))
        bounded_limit = max(1, min(500, int(limit)))
        messages: list[dict[str, Any]] = []

        with self._lock:
            with exclusive_path_lock(self.path):
                with self.path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        raw = line.strip()
                        if not raw:
                            continue
                        row = json.loads(raw)
                        seq = int(row.get("seq", 0))
                        if seq <= bounded_after:
                            continue
                        messages.append(row)
                        if len(messages) >= bounded_limit:
                            break

        next_seq = bounded_after
        if messages:
            next_seq = int(messages[-1]["seq"])

        return {
            "messages": messages,
            "after_seq": bounded_after,
            "next_seq": next_seq,
        }

    def _bootstrap_tail(self) -> None:
        with self._lock:
            with exclusive_path_lock(self.path):
                self._last_seq, self._last_hash = self._tail_state_unlocked()

    def _tail_state_unlocked(self) -> tuple[int, str]:
        last_non_empty = ""
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if raw:
                    last_non_empty = raw

        if not last_non_empty:
            return 0, "GENESIS"

        row = json.loads(last_non_empty)
        seq = int(row.get("seq", 0))
        raw_hash = str(row.get("hash", ""))
        if raw_hash:
            return seq, raw_hash

        payload = {k: v for k, v in row.items() if k != "hash"}
        payload.setdefault("prev_hash", "GENESIS")
        return seq, self._hash_payload(payload)

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()
