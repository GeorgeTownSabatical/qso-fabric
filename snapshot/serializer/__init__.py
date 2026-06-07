from __future__ import annotations

from typing import Any, Dict

from qff.serializer.service import QFFSerializer


def serialize_snapshot(payload: Dict[str, Any]) -> bytes:
    return QFFSerializer().serialize(payload)
