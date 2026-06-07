from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Iterable

from core.identity.events import IDENTITY_EVENT_SCHEMA, IdentityEventType
from core.identity.model import (
    IdentityKernelEvent,
    IdentityLifecycleStatus,
    IdentityLinkRelationship,
    IdentityLinkStatus,
)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _state_hash(state: Dict[str, Any]) -> str:
    payload = deepcopy(state)
    payload.pop("state_hash", None)
    return _canonical_hash(payload)


def serialize_identity_event(event: IdentityKernelEvent) -> Dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "actor": event.actor,
        "policy_version": event.policy_version,
        "payload": deepcopy(event.payload),
        "node_id": event.node_id,
        "timestamp": event.timestamp,
    }


def empty_identity_state(uri: str, policy_version: str = "v1") -> Dict[str, Any]:
    state = {
        "identity_uri": uri,
        "metadata": {},
        "credential_refs": {},
        "entitlements": {},
        "key_refs": [],
        "entanglement_links": {},
        "measurements": [],
        "revocation_state": {
            "status": IdentityLifecycleStatus.ACTIVE.value,
            "reason": None,
            "at_event_id": None,
        },
        "policy_version_pointer": policy_version,
        "timeline_log": [],
        "state_hash": "",
    }
    state["state_hash"] = _state_hash(state)
    return state


def _require_payload_fields(event: IdentityKernelEvent) -> None:
    required = IDENTITY_EVENT_SCHEMA[event.event_type]
    missing = [field for field in required if field not in event.payload]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing required payload fields for {event.event_type.value}: {joined}")


def _is_created(state: Dict[str, Any]) -> bool:
    return bool(state.get("metadata"))


def _lifecycle(state: Dict[str, Any]) -> str:
    revocation_state = state.get("revocation_state", {})
    return str(revocation_state.get("status", IdentityLifecycleStatus.ACTIVE.value))


def _validate_lifecycle_transition(state: Dict[str, Any], event: IdentityKernelEvent) -> None:
    lifecycle = _lifecycle(state)
    if lifecycle == IdentityLifecycleStatus.ARCHIVED.value:
        raise ValueError("identity is archived; no further events are allowed")
    if lifecycle == IdentityLifecycleStatus.FROZEN.value and event.event_type not in {
        IdentityEventType.MEASURE_VERIFY,
        IdentityEventType.LINK_REVOKE,
        IdentityEventType.IDENTITY_ARCHIVE,
    }:
        raise ValueError(f"identity is frozen; event {event.event_type.value} is not allowed")


def _relationship_value(value: str) -> str:
    return IdentityLinkRelationship(str(value)).value


def apply_identity_event(state: Dict[str, Any], event: IdentityKernelEvent) -> Dict[str, Any]:
    _require_payload_fields(event)
    next_state = deepcopy(state)

    created = _is_created(next_state)
    if not created and event.event_type != IdentityEventType.IDENTITY_CREATE:
        raise ValueError("identity must begin with IDENTITY_CREATE")
    if created and event.event_type == IdentityEventType.IDENTITY_CREATE:
        raise ValueError("IDENTITY_CREATE already applied")

    if event.event_type != IdentityEventType.IDENTITY_CREATE:
        _validate_lifecycle_transition(next_state, event)

    if event.event_type == IdentityEventType.IDENTITY_CREATE:
        immutable_core = deepcopy(dict(event.payload.get("immutable_core", {})))
        if not immutable_core:
            raise ValueError("IDENTITY_CREATE requires non-empty immutable_core")
        next_state["metadata"] = immutable_core
        next_state["metadata"]["created_by"] = event.actor
        next_state["metadata"]["created_event_id"] = event.event_id

    elif event.event_type == IdentityEventType.KEY_ROTATE:
        next_state["key_refs"].append(
            {
                "key_ref": str(event.payload["key_ref"]),
                "rotated_by": event.actor,
                "event_id": event.event_id,
            }
        )

    elif event.event_type == IdentityEventType.CREDENTIAL_ISSUE:
        credential_id = str(event.payload["credential_id"])
        next_state["credential_refs"][credential_id] = {
            "status": IdentityLinkStatus.ACTIVE.value,
            "issued_by": event.actor,
            "issued_event_id": event.event_id,
            "data": deepcopy(dict(event.payload)),
        }

    elif event.event_type == IdentityEventType.CREDENTIAL_REVOKE:
        credential_id = str(event.payload["credential_id"])
        current = next_state["credential_refs"].get(credential_id)
        if current is None:
            raise ValueError(f"credential not found: {credential_id}")
        current["status"] = IdentityLinkStatus.INERT.value
        current["revoked_by"] = event.actor
        current["revoked_event_id"] = event.event_id
        current["revocation_reason"] = event.payload.get("reason")

    elif event.event_type == IdentityEventType.ENTITLEMENT_GRANT:
        entitlement_id = str(event.payload["entitlement_id"])
        next_state["entitlements"][entitlement_id] = {
            "status": IdentityLinkStatus.ACTIVE.value,
            "granted_by": event.actor,
            "event_id": event.event_id,
            "data": deepcopy(dict(event.payload)),
        }

    elif event.event_type == IdentityEventType.ENTITLEMENT_REVOKE:
        entitlement_id = str(event.payload["entitlement_id"])
        entitlement = next_state["entitlements"].get(entitlement_id)
        if entitlement is None:
            raise ValueError(f"entitlement not found: {entitlement_id}")
        entitlement["status"] = IdentityLinkStatus.INERT.value
        entitlement["revoked_by"] = event.actor
        entitlement["revoked_event_id"] = event.event_id

    elif event.event_type == IdentityEventType.LINK_ATTACH:
        link_id = str(event.payload["link_id"])
        links = next_state["entanglement_links"]
        record = links.get(link_id, {})
        record.update(
            {
                "link_id": link_id,
                "target_uri": str(event.payload["target_uri"]),
                "relationship": _relationship_value(str(event.payload["relationship"])),
                "status": IdentityLinkStatus.ACTIVE.value,
                "attached_by": event.actor,
                "attach_event_id": event.event_id,
                "data": deepcopy(dict(event.payload)),
            }
        )
        record.pop("revoked_by", None)
        record.pop("revoked_event_id", None)
        record.pop("revocation_reason", None)
        links[link_id] = record

    elif event.event_type == IdentityEventType.LINK_REVOKE:
        link_id = str(event.payload["link_id"])
        link = next_state["entanglement_links"].get(link_id)
        if link is None:
            raise ValueError(f"link not found: {link_id}")
        link["status"] = IdentityLinkStatus.INERT.value
        link["revoked_by"] = event.actor
        link["revoked_event_id"] = event.event_id
        link["revocation_reason"] = event.payload.get("reason")

    elif event.event_type == IdentityEventType.MEASURE_VERIFY:
        next_state["measurements"].append(
            {
                "measurement_id": str(event.payload["measurement_id"]),
                "result": bool(event.payload.get("result", True)),
                "measured_by": event.actor,
                "event_id": event.event_id,
                "data": deepcopy(dict(event.payload)),
            }
        )

    elif event.event_type == IdentityEventType.IDENTITY_FREEZE:
        next_state["revocation_state"]["status"] = IdentityLifecycleStatus.FROZEN.value
        next_state["revocation_state"]["reason"] = event.payload.get("reason")
        next_state["revocation_state"]["at_event_id"] = event.event_id

    elif event.event_type == IdentityEventType.IDENTITY_ARCHIVE:
        next_state["revocation_state"]["status"] = IdentityLifecycleStatus.ARCHIVED.value
        next_state["revocation_state"]["reason"] = event.payload.get("reason")
        next_state["revocation_state"]["at_event_id"] = event.event_id

    timeline = next_state["timeline_log"]
    timeline.append(
        {
            "sequence": len(timeline) + 1,
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "actor": event.actor,
            "policy_version": event.policy_version,
            "node_id": event.node_id,
            "timestamp": event.timestamp,
            "payload": deepcopy(event.payload),
        }
    )
    next_state["policy_version_pointer"] = event.policy_version
    next_state["state_hash"] = _state_hash(next_state)
    return next_state


def reduce_identity_timeline(uri: str, events: Iterable[IdentityKernelEvent], policy_version: str = "v1") -> Dict[str, Any]:
    state = empty_identity_state(uri, policy_version=policy_version)
    for event in events:
        state = apply_identity_event(state, event)
    return state

