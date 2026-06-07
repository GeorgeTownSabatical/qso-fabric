"""File-backed task queue dispatcher for control node."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import uuid


class TaskDispatcher:
    def __init__(self, queue_path: Path, result_path: Path):
        self.queue_path = queue_path
        self.result_path = result_path
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.result_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8").strip()
        return json.loads(text) if text else []

    def _save(self, path: Path, rows: list[dict]) -> None:
        path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def publish(self, task_type: str, payload: dict) -> dict:
        rows = self._load(self.queue_path)
        task = {
            "task_id": str(uuid.uuid4()),
            "task_type": task_type,
            "payload": payload,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        rows.append(task)
        self._save(self.queue_path, rows)
        return task

    def fetch_next(self) -> dict | None:
        rows = self._load(self.queue_path)
        for row in rows:
            if row.get("status") == "queued":
                row["status"] = "in_progress"
                row["started_at"] = datetime.now(timezone.utc).isoformat()
                self._save(self.queue_path, rows)
                return row
        return None

    def complete(self, task_id: str, result: dict, ok: bool) -> None:
        queue = self._load(self.queue_path)
        for row in queue:
            if row.get("task_id") == task_id:
                row["status"] = "done" if ok else "failed"
                row["finished_at"] = datetime.now(timezone.utc).isoformat()
        self._save(self.queue_path, queue)

        results = self._load(self.result_path)
        results.append({
            "task_id": task_id,
            "ok": ok,
            "result": result,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        self._save(self.result_path, results)

    def queue_state(self) -> list[dict]:
        return self._load(self.queue_path)

    def results(self) -> list[dict]:
        return self._load(self.result_path)
