from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List


@dataclass(frozen=True)
class AuditRecord:
    at: str
    actor: str
    action: str
    object_uri: str
    detail: Dict[str, Any]


class AuditLedger:
    def __init__(self) -> None:
        self._rows: List[AuditRecord] = []
        self._lock = RLock()

    def append(self, actor: str, action: str, object_uri: str, detail: Dict[str, Any] | None = None) -> None:
        row = AuditRecord(
            at=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            action=action,
            object_uri=object_uri,
            detail=dict(detail or {}),
        )
        with self._lock:
            self._rows.append(row)

    def query(self, actor: str | None = None, object_uri: str | None = None) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        with self._lock:
            for row in self._rows:
                if actor is not None and row.actor != actor:
                    continue
                if object_uri is not None and row.object_uri != object_uri:
                    continue
                out.append(
                    {
                        "at": row.at,
                        "actor": row.actor,
                        "action": row.action,
                        "object_uri": row.object_uri,
                        "detail": dict(row.detail),
                    }
                )
        return out
