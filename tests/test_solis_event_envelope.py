from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from api.schemas.models import QSOEvent
from services.event_log.signing import qso_event_payload
from solis.shared.canonical_json import canonical_json
from solis.shared.event_envelope import QSOEventEnvelope, REQUIRED_EVENT_FIELDS, validate_event_envelope
from solis.shared.event_schema import minimal_event_schema


def test_minimal_event_schema_requires_canonical_envelope_fields() -> None:
    schema = minimal_event_schema()
    required = set(schema["required"])
    assert set(REQUIRED_EVENT_FIELDS).issubset(required)


def test_event_envelope_canonical_json_is_deterministic() -> None:
    base = QSOEventEnvelope.new(
        event_id="evt-1",
        timestamp="2026-02-25T00:00:00+00:00",
        actor="tester",
        object_uri="qso://solis.star.demo",
        delta={"b": 2, "a": 1},
        signature="sig",
        policy_version="v1",
    )
    same = QSOEventEnvelope.from_mapping(
        {
            "policy_version": "v1",
            "actor": "tester",
            "event_id": "evt-1",
            "object_uri": "qso://solis.star.demo",
            "timestamp": "2026-02-25T00:00:00+00:00",
            "delta": {"a": 1, "b": 2},
            "signature": "sig",
        }
    )
    assert base.canonical_json() == same.canonical_json()


def test_qso_event_payload_is_canonical_and_excludes_signature() -> None:
    event = QSOEvent(
        event_id="evt-2",
        timestamp=datetime(2026, 2, 25, tzinfo=timezone.utc),
        actor="tester",
        object_uri="qso://solis.star.demo",
        delta={"x": 7, "y": 9},
        signature="signed-value",
        policy_version="v1",
        node_id="node-a",
    )
    payload = qso_event_payload(event)
    decoded = json.loads(payload)
    assert "signature" not in decoded
    assert decoded["event_id"] == "evt-2"
    assert decoded["policy_version"] == "v1"
    assert decoded["node_id"] == "node-a"
    assert decoded["schema_version"] == "1.0"
    assert payload == canonical_json(decoded)


def test_validate_event_envelope_rejects_missing_required_fields() -> None:
    with pytest.raises(ValueError):
        validate_event_envelope(
            {
                "event_id": "evt-3",
                "timestamp": "2026-02-25T00:00:00+00:00",
                "actor": "tester",
                "object_uri": "qso://solis.star.demo",
                "delta": {},
                "signature": "sig",
            }
        )
