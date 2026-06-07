from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Dict

from api.schemas.models import QSOEvent, QSOObject
from core.identity.events import IdentityEventType, parse_identity_event_type
from core.identity.model import IdentityKernelEvent
from core.identity.reducer import empty_identity_state, reduce_identity_timeline, serialize_identity_event
from core.identity.uri import validate_identity_person_uri
from services.crypto_access.service import CryptoAccessService
from services.event_log.clock import LogicalClock
from services.event_log.service import EventLogService
from services.event_log.signing import qso_event_payload
from services.registry.service import RegistryService


def _deep_merge(target: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(target)
    for key, value in delta.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _event_id() -> str:
    gen = getattr(uuid, "uuid7", None)
    return str(gen() if callable(gen) else uuid.uuid4())


class StateEngineService:
    def __init__(
        self,
        registry: RegistryService,
        event_log: EventLogService,
        crypto: CryptoAccessService,
        clock: LogicalClock | None = None,
    ) -> None:
        self.registry = registry
        self.event_log = event_log
        self.crypto = crypto
        self.clock = clock or LogicalClock()
        self._policy_resolver: Callable[[], Dict[str, Any]] | None = None

    def set_policy_resolver(self, resolver: Callable[[], Dict[str, Any]]) -> None:
        self._policy_resolver = resolver

    def create_object(self, uri: str, schema: Dict[str, Any], actor: str = "system") -> QSOObject:
        identity_layer = {
            "uri": uri,
            "created_by": actor,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        obj = QSOObject(
            uri=uri,
            schema=schema,
            identity_layer=identity_layer,
            state_layer={},
            timeline_layer=[],
            entanglement_layer=[],
            snapshot_layer={},
        )
        return self.registry.create(obj)

    def create_identity(
        self,
        uri: str,
        immutable_core: Dict[str, Any],
        actor: str = "system",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> QSOEvent:
        validate_identity_person_uri(uri)
        if self.registry.has(uri):
            raise ValueError(f"identity already exists: {uri}")
        self.create_object(uri, {"type": "identity", "subtype": "person"}, actor=actor)
        return self.apply_identity_event(
            uri=uri,
            event_type=IdentityEventType.IDENTITY_CREATE,
            payload={"immutable_core": deepcopy(immutable_core)},
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def read(self, uri: str) -> QSOObject:
        return self.registry.read(uri)

    def apply_identity_event(
        self,
        uri: str,
        event_type: str | IdentityEventType,
        payload: Dict[str, Any],
        actor: str,
        policy_version: str,
        node_id: str = "local",
    ) -> QSOEvent:
        validate_identity_person_uri(uri)
        if not self.registry.has(uri):
            raise KeyError(f"identity not found: {uri}")

        normalized_type = parse_identity_event_type(event_type)
        identity_event = IdentityKernelEvent(
            event_id=_event_id(),
            event_type=normalized_type,
            actor=actor,
            policy_version=policy_version,
            payload=deepcopy(payload),
            node_id=node_id,
            timestamp=self.clock.next_datetime().isoformat(),
        )
        prior_events = self._identity_kernel_events(uri, strict=True)
        next_state = reduce_identity_timeline(uri, [*prior_events, identity_event], policy_version=policy_version)
        delta = {
            "identity_event": serialize_identity_event(identity_event),
            "identity_runtime": next_state,
        }
        return self.patch(
            uri=uri,
            delta=delta,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def patch(self, uri: str, delta: Dict[str, Any], actor: str, policy_version: str, node_id: str = "local") -> QSOEvent:
        if self._policy_resolver is not None:
            policy = self._policy_resolver()
            expected_policy_version = str(policy.get("version", policy_version))
            if policy_version != expected_policy_version:
                raise ValueError(f"policy version mismatch: event={policy_version}, runtime={expected_policy_version}")
            allowed = policy.get("allowed_actors")
            if isinstance(allowed, list) and allowed and actor not in allowed:
                raise ValueError(f"actor not authorized by policy: {actor}")

        obj = self.registry.read(uri)
        next_state = _deep_merge(obj.state_layer, delta)

        event = QSOEvent(
            event_id=_event_id(),
            timestamp=self.clock.next_datetime(),
            actor=actor,
            object_uri=uri,
            delta=delta,
            signature="",
            policy_version=policy_version,
            node_id=node_id,
        )
        event.signature = self.crypto.sign(qso_event_payload(event))

        obj.state_layer = next_state
        obj.timeline_layer.append(event)
        self.registry.update(obj)
        self.event_log.append(event)
        return event

    def rebuild_identity_state(self, uri: str, strict: bool = True) -> Dict[str, Any]:
        validate_identity_person_uri(uri)
        events = self._identity_kernel_events(uri, strict=strict)
        if not events:
            return empty_identity_state(uri)
        return reduce_identity_timeline(uri, events, policy_version=events[0].policy_version)

    def _identity_kernel_events(self, uri: str, strict: bool = True) -> list[IdentityKernelEvent]:
        kernel_events: list[IdentityKernelEvent] = []
        for event in self.event_log.replay(uri, strict=strict):
            raw = event.delta.get("identity_event")
            if not isinstance(raw, dict):
                continue

            raw_payload = raw.get("payload", {})
            payload = deepcopy(raw_payload if isinstance(raw_payload, dict) else {})
            raw_event_id = raw.get("event_id")
            raw_type = raw.get("event_type")
            if raw_type is None:
                raise ValueError("identity_event missing event_type")

            kernel_events.append(
                IdentityKernelEvent(
                    event_id=str(raw_event_id) if raw_event_id is not None else event.event_id,
                    event_type=parse_identity_event_type(str(raw_type)),
                    actor=str(raw.get("actor", event.actor)),
                    policy_version=str(raw.get("policy_version", event.policy_version)),
                    payload=payload,
                    node_id=str(raw.get("node_id", event.node_id)),
                    timestamp=str(raw.get("timestamp")) if raw.get("timestamp") is not None else event.timestamp.isoformat(),
                )
            )
        return kernel_events

    def rebuild_from_log(self, uri: str, strict: bool = True) -> Dict[str, Any]:
        state: Dict[str, Any] = {}
        for event in self.event_log.replay(uri, strict=strict):
            state = _deep_merge(state, event.delta)
        return state
