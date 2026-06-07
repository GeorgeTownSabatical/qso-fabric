from __future__ import annotations

from typing import Any, Dict, TypedDict

from solis.schemas import SCHEMA_VERSION
from solis.shared.event_envelope import REQUIRED_EVENT_FIELDS


class QSOEventRecord(TypedDict):
    schema_version: str
    event_id: str
    timestamp: str
    actor: str
    object_uri: str
    delta: Dict[str, Any]
    signature: str
    policy_version: str
    node_id: str


def minimal_event_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": list(REQUIRED_EVENT_FIELDS),
        "properties": {
            "schema_version": {"type": "string", "default": SCHEMA_VERSION},
            "event_id": {"type": "string"},
            "timestamp": {"type": "string"},
            "actor": {"type": "string"},
            "object_uri": {"type": "string"},
            "delta": {"type": "object"},
            "signature": {"type": "string"},
            "policy_version": {"type": "string"},
            "node_id": {"type": "string"},
        },
    }
