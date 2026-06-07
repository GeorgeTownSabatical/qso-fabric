from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from solis.schemas import SCHEMA_VERSION
from solis.shared.canonical_json import canonical_json

REQUIRED_EVENT_FIELDS: tuple[str, ...] = (
    "event_id",
    "timestamp",
    "actor",
    "object_uri",
    "delta",
    "signature",
    "policy_version",
)


@dataclass(frozen=True)
class QSOEventEnvelope:
    event_id: str
    timestamp: str
    actor: str
    object_uri: str
    delta: dict[str, Any]
    signature: str
    policy_version: str
    node_id: str = "local"
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def new(
        cls,
        *,
        event_id: str,
        actor: str,
        object_uri: str,
        delta: Mapping[str, Any],
        signature: str,
        policy_version: str,
        node_id: str = "local",
        timestamp: str | None = None,
        schema_version: str = SCHEMA_VERSION,
    ) -> "QSOEventEnvelope":
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        envelope = cls(
            event_id=str(event_id),
            timestamp=str(timestamp),
            actor=str(actor),
            object_uri=str(object_uri),
            delta={str(key): value for key, value in dict(delta).items()},
            signature=str(signature),
            policy_version=str(policy_version),
            node_id=str(node_id),
            schema_version=str(schema_version),
        )
        validate_event_envelope(envelope.as_dict(), allow_empty_signature=not bool(str(signature).strip()))
        return envelope

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "QSOEventEnvelope":
        validate_event_envelope(value)
        return cls(
            event_id=str(value["event_id"]),
            timestamp=str(value["timestamp"]),
            actor=str(value["actor"]),
            object_uri=str(value["object_uri"]),
            delta=dict(value["delta"]),
            signature=str(value["signature"]),
            policy_version=str(value["policy_version"]),
            node_id=str(value.get("node_id", "local")),
            schema_version=str(value.get("schema_version", SCHEMA_VERSION)),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "object_uri": self.object_uri,
            "delta": dict(self.delta),
            "signature": self.signature,
            "policy_version": self.policy_version,
            "node_id": self.node_id,
        }

    def canonical_json(self) -> str:
        return canonical_json(self.as_dict())

    def signing_payload(self) -> str:
        payload = self.as_dict()
        payload.pop("signature", None)
        return canonical_json(payload)


def validate_event_envelope(value: Mapping[str, Any], *, allow_empty_signature: bool = False) -> None:
    for field in REQUIRED_EVENT_FIELDS:
        if field not in value:
            raise ValueError(f"event envelope missing required field '{field}'")

    if not isinstance(value["delta"], Mapping):
        raise ValueError("event envelope field 'delta' must be object")

    fields = ["event_id", "timestamp", "actor", "object_uri", "policy_version"]
    if not allow_empty_signature:
        fields.append("signature")
    for field in fields:
        if not str(value[field]).strip():
            raise ValueError(f"event envelope field '{field}' must be non-empty")
