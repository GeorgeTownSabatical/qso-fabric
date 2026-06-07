"""Runtime bridge for executing persisted fabric payloads through QSO."""

from __future__ import annotations

from typing import Any

from services.quantum.fabric.fabric import QSOFabric
from services.quantum.fabric.gluing import GluingEngine


def execute_fabric_payload(
    payload: dict[str, Any],
    *,
    coherence_threshold: float = 0.8,
) -> dict[str, Any]:
    """Run gluing/coherence analysis on a serialized fabric payload."""

    if "fabric_payload" in payload:
        raw_fabric = dict(payload["fabric_payload"])
    else:
        raw_fabric = {
            "id": str(payload.get("fabric_id", payload.get("uri", "fabric.runtime"))),
            "patches": dict(payload.get("patches", {})),
            "overlaps": dict(payload.get("overlaps", {})),
            "metadata": dict(payload.get("metadata", {})),
        }
    fabric = QSOFabric.from_json_dict(raw_fabric)
    return GluingEngine(coherence_threshold=coherence_threshold).analyze(fabric)
