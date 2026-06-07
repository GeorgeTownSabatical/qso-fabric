from __future__ import annotations

import json

from api.schemas.models import PolicyMutationEvent, QSOEvent
from solis.shared.event_envelope import QSOEventEnvelope


def qso_event_payload(event: QSOEvent) -> str:
    envelope = QSOEventEnvelope.new(
        event_id=event.event_id,
        timestamp=event.timestamp.isoformat(),
        actor=event.actor,
        object_uri=event.object_uri,
        delta=event.delta,
        signature=event.signature,
        policy_version=event.policy_version,
        node_id=event.node_id,
    )
    return envelope.signing_payload()


def policy_mutation_payload(event: PolicyMutationEvent) -> str:
    return json.dumps(
        {
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "actor": event.actor,
            "node_id": event.node_id,
            "from_version": event.from_version,
            "to_version": event.to_version,
            "policy_delta": event.policy_delta,
        },
        sort_keys=True,
    )
