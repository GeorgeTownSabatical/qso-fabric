from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any, Dict, List

from api.schemas.models import PolicyMutationEvent, QSOEvent
from services.crypto_access.service import CryptoAccessService
from services.event_log.clock import LogicalClock
from services.event_log.service import EventLogService
from services.event_log.signing import policy_mutation_payload, qso_event_payload


POLICY_URI = "qso://policy.global"


def _version_num(version: str) -> int:
    if version.startswith("v"):
        try:
            return int(version[1:])
        except ValueError:
            return -1
    return -1


class PolicySyncService:
    def __init__(self, event_log: EventLogService, crypto: CryptoAccessService, clock: LogicalClock | None = None) -> None:
        self._global_policy: Dict[str, Any] = {"version": "v1", "mode": "balanced"}
        self._history: List[PolicyMutationEvent] = []
        self.event_log = event_log
        self.crypto = crypto
        self.clock = clock or LogicalClock()

    def publish(self, policy: Dict[str, Any], actor: str = "gdml", node_id: str = "local") -> Dict[str, Any]:
        from_version = str(self._global_policy.get("version", "v1"))
        to_version = str(policy.get("version", from_version))
        if _version_num(to_version) <= _version_num(from_version):
            raise ValueError(f"policy version must be monotonic: {from_version} -> {to_version}")

        mut = PolicyMutationEvent(
            event_id=str(getattr(uuid, "uuid7", uuid.uuid4)()),
            timestamp=self.clock.next_datetime(),
            actor=actor,
            node_id=node_id,
            from_version=from_version,
            to_version=to_version,
            policy_delta=deepcopy(policy),
            signature="",
        )
        mut.signature = self.crypto.sign(policy_mutation_payload(mut))

        self._history.append(mut)
        self._global_policy = dict(policy)

        activation_index = len(self.event_log.timeline(POLICY_URI)) + 1
        event = QSOEvent(
            event_id=mut.event_id,
            timestamp=mut.timestamp,
            actor=actor,
            object_uri=POLICY_URI,
            delta={
                "event_type": "policy_mutation",
                "from_version": from_version,
                "to_version": to_version,
                "policy": deepcopy(policy),
                "node_id": node_id,
                "activation_index": activation_index,
                "effective_after_event": activation_index,
            },
            signature="",
            policy_version=to_version,
            node_id=node_id,
        )
        event.signature = self.crypto.sign(qso_event_payload(event))
        self.event_log.append(event)

        return deepcopy(self._global_policy)

    def rollback(self, target_version: str, actor: str = "rollback", node_id: str = "local") -> Dict[str, Any]:
        candidates = [e for e in self._history if e.to_version == target_version]
        if not candidates:
            raise ValueError(f"target policy version not found: {target_version}")
        target = candidates[-1]
        return self.publish(dict(target.policy_delta), actor=actor, node_id=node_id)

    def current(self) -> Dict[str, Any]:
        return deepcopy(self._global_policy)

    def history(self) -> List[PolicyMutationEvent]:
        return deepcopy(self._history)
