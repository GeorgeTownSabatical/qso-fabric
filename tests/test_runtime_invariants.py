from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from api.schemas.models import EntanglementLink, QSOEvent
from services.event_log.signing import qso_event_payload
from services.runtime import QSOFabricRuntime


def test_replay_rejects_invalid_signature_in_strict_mode() -> None:
    runtime = QSOFabricRuntime()
    uri = "qso://ai.model.core"
    runtime.state_engine.create_object(uri, {"type": "model"})

    runtime.state_engine.patch(uri, {"x": 1}, actor="a", policy_version="v1")

    bad = QSOEvent(
        event_id="bad",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        actor="a",
        object_uri=uri,
        delta={"x": 2},
        signature="invalid",
        policy_version="v1",
    )
    runtime.event_log.append(bad)

    with pytest.raises(ValueError):
        runtime.event_log.replay(uri, strict=True)

    relaxed = runtime.event_log.replay(uri, strict=False)
    assert len(relaxed) == 1


def test_entanglement_cycle_is_rejected() -> None:
    runtime = QSOFabricRuntime()
    runtime.entanglement.entangle(EntanglementLink(source_uri="qso://a", target_uri="qso://b", relationship="r"))
    runtime.entanglement.entangle(EntanglementLink(source_uri="qso://b", target_uri="qso://c", relationship="r"))

    with pytest.raises(ValueError):
        runtime.entanglement.entangle(EntanglementLink(source_uri="qso://c", target_uri="qso://a", relationship="r"))


def test_policy_mutations_are_logged_and_monotonic() -> None:
    runtime = QSOFabricRuntime()

    updated = runtime.gdml.policy_sync.publish({"version": "v2", "mode": "x"}, actor="gdml", node_id="n1")
    assert updated["version"] == "v2"

    timeline = runtime.event_log.timeline("qso://policy.global")
    assert timeline
    assert timeline[-1].delta["event_type"] == "policy_mutation"

    with pytest.raises(ValueError):
        runtime.gdml.policy_sync.publish({"version": "v1", "mode": "rollback"}, actor="gdml", node_id="n1")


def test_replay_canonical_ordering() -> None:
    runtime = QSOFabricRuntime()
    uri = "qso://ordering.test"

    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    e2 = QSOEvent(
        event_id="b",
        timestamp=t0 + timedelta(seconds=1),
        actor="a",
        object_uri=uri,
        delta={"v": 2},
        signature="",
        policy_version="v1",
    )
    e1 = QSOEvent(
        event_id="a",
        timestamp=t0,
        actor="a",
        object_uri=uri,
        delta={"v": 1},
        signature="",
        policy_version="v1",
    )
    e1.signature = runtime.crypto.sign(qso_event_payload(e1))
    e2.signature = runtime.crypto.sign(qso_event_payload(e2))

    runtime.event_log.append(e2)
    runtime.event_log.append(e1)

    replayed = runtime.event_log.replay(uri, strict=True)
    assert [e.event_id for e in replayed] == ["a", "b"]
