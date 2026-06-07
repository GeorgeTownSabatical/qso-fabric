from __future__ import annotations

import pytest

from core.identity import CANONICAL_IDENTITY_EVENT_SEQUENCE, IdentityEventType
from services.runtime import QSOFabricRuntime


def test_identity_event_taxonomy_is_frozen() -> None:
    assert tuple(event.value for event in CANONICAL_IDENTITY_EVENT_SEQUENCE) == (
        "IDENTITY_CREATE",
        "KEY_ROTATE",
        "CREDENTIAL_ISSUE",
        "CREDENTIAL_REVOKE",
        "ENTITLEMENT_GRANT",
        "ENTITLEMENT_REVOKE",
        "LINK_ATTACH",
        "LINK_REVOKE",
        "MEASURE_VERIFY",
        "IDENTITY_FREEZE",
        "IDENTITY_ARCHIVE",
    )


def test_identity_link_revoke_is_inert_and_topology_preserved() -> None:
    runtime = QSOFabricRuntime()
    uri = "qso://identity.person.hash_001"

    runtime.state_engine.create_identity(uri, {"subject_ref": "hash_001"}, actor="authority", policy_version="v1")
    runtime.state_engine.apply_identity_event(
        uri=uri,
        event_type=IdentityEventType.LINK_ATTACH,
        payload={
            "link_id": "device_primary",
            "target_uri": "qso://identity.device.device_001",
            "relationship": "device_binding",
        },
        actor="authority",
        policy_version="v1",
    )
    runtime.state_engine.apply_identity_event(
        uri=uri,
        event_type=IdentityEventType.LINK_REVOKE,
        payload={"link_id": "device_primary", "reason": "compromised"},
        actor="authority",
        policy_version="v1",
    )

    state = runtime.state_engine.rebuild_identity_state(uri)
    link = state["entanglement_links"]["device_primary"]
    assert link["status"] == "inert"
    assert link["target_uri"] == "qso://identity.device.device_001"
    assert link["relationship"] == "device_binding"

    runtime.state_engine.apply_identity_event(
        uri=uri,
        event_type=IdentityEventType.LINK_ATTACH,
        payload={
            "link_id": "device_primary",
            "target_uri": "qso://identity.device.device_001",
            "relationship": "device_binding",
        },
        actor="authority",
        policy_version="v1",
    )
    reattached = runtime.state_engine.rebuild_identity_state(uri)["entanglement_links"]["device_primary"]
    assert reattached["status"] == "active"


def test_identity_replay_is_deterministic() -> None:
    runtime = QSOFabricRuntime()
    uri = "qso://identity.person.hash_002"

    runtime.state_engine.create_identity(uri, {"subject_ref": "hash_002"}, actor="authority", policy_version="v1")
    runtime.state_engine.apply_identity_event(
        uri=uri,
        event_type="KEY_ROTATE",
        payload={"key_ref": "key-v2"},
        actor="authority",
        policy_version="v1",
    )
    runtime.state_engine.apply_identity_event(
        uri=uri,
        event_type="CREDENTIAL_ISSUE",
        payload={"credential_id": "cred-001", "issuer": "authority"},
        actor="authority",
        policy_version="v1",
    )

    state_a = runtime.state_engine.rebuild_identity_state(uri)
    state_b = runtime.state_engine.rebuild_identity_state(uri)
    assert state_a == state_b
    assert state_a["state_hash"] == state_b["state_hash"]

    obj = runtime.state_engine.read(uri)
    assert obj.state_layer["identity_runtime"]["state_hash"] == state_a["state_hash"]


def test_identity_uri_and_lifecycle_enforcement() -> None:
    runtime = QSOFabricRuntime()

    with pytest.raises(ValueError):
        runtime.state_engine.create_identity(
            "qso://identity.user.bad",
            {"subject_ref": "bad"},
            actor="authority",
            policy_version="v1",
        )

    uri = "qso://identity.person.hash_003"
    runtime.state_engine.create_identity(uri, {"subject_ref": "hash_003"}, actor="authority", policy_version="v1")
    runtime.state_engine.apply_identity_event(
        uri=uri,
        event_type="IDENTITY_FREEZE",
        payload={"reason": "investigation"},
        actor="authority",
        policy_version="v1",
    )

    with pytest.raises(ValueError):
        runtime.state_engine.apply_identity_event(
            uri=uri,
            event_type="ENTITLEMENT_GRANT",
            payload={"entitlement_id": "clearance.top_secret"},
            actor="authority",
            policy_version="v1",
        )

