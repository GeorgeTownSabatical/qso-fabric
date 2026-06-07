from __future__ import annotations

from typing import Any, Dict

from qff.deserializer.service import QFFDeserializer


def deserialize_snapshot(blob: bytes) -> Dict[str, Any]:
    return QFFDeserializer().deserialize(blob)
