from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


class CircuitRegistry:
    def __init__(self) -> None:
        self._circuits: dict[str, dict[str, Any]] = {}

    def register(self, *, mode: str, exit_fingerprint: str = "") -> str:
        circuit_id = str(uuid.uuid4())
        self._circuits[circuit_id] = {
            "circuit_id": circuit_id,
            "mode": str(mode),
            "exit_fingerprint": str(exit_fingerprint),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "latency_samples": [],
            "error_count": 0,
        }
        return circuit_id

    def record_sample(self, circuit_id: str, *, latency_ms: float, ok: bool) -> None:
        if circuit_id not in self._circuits:
            return
        row = self._circuits[circuit_id]
        row["latency_samples"].append(float(latency_ms))
        if not ok:
            row["error_count"] = int(row.get("error_count", 0)) + 1

    def list(self) -> list[dict[str, Any]]:
        return [dict(value) for _, value in sorted(self._circuits.items())]

    def read(self, circuit_id: str) -> dict[str, Any] | None:
        value = self._circuits.get(circuit_id)
        return None if value is None else dict(value)
