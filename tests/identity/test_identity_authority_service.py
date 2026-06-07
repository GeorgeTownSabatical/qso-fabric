from __future__ import annotations

import pytest

from services.runtime import QSOFabricRuntime


def test_authority_issues_and_revokes_credential() -> None:
    runtime = QSOFabricRuntime()
    uri = "qso://identity.person.authority_001"

    runtime.identity_authority.create_identity(
        uri=uri,
        immutable_core={"subject_ref": "authority_001"},
        actor="authority://root",
        policy_version="v1",
    )
    runtime.identity_authority.issue_credential(
        uri=uri,
        credential_id="cred.employee.badge",
        credential_body={"issuer": "authority://root", "scope": "building_a"},
        actor="authority://root",
        policy_version="v1",
    )
    runtime.identity_authority.revoke_credential(
        uri=uri,
        credential_id="cred.employee.badge",
        reason="badge compromised",
        actor="authority://root",
        policy_version="v1",
    )

    state = runtime.state_engine.rebuild_identity_state(uri)
    credential = state["credential_refs"]["cred.employee.badge"]
    assert credential["status"] == "inert"
    assert credential["revocation_reason"] == "badge compromised"
    assert state["policy_version_pointer"] == "v1"


def test_authority_policy_publish_enforces_actor_and_version() -> None:
    runtime = QSOFabricRuntime()
    published = runtime.identity_authority.publish_policy(
        {
            "version": "v2",
            "mode": "zero-trust",
            "allowed_actors": ["authority://root"],
        },
        actor="governance://board",
        node_id="policy-cluster",
    )
    assert published["version"] == "v2"

    uri = "qso://identity.person.authority_002"
    runtime.identity_authority.create_identity(
        uri=uri,
        immutable_core={"subject_ref": "authority_002"},
        actor="authority://root",
        policy_version="v2",
    )

    with pytest.raises(ValueError, match="actor not authorized by policy"):
        runtime.identity_authority.issue_credential(
            uri=uri,
            credential_id="cred.a",
            actor="authority://rogue",
            policy_version="v2",
        )

    with pytest.raises(ValueError, match="policy version mismatch"):
        runtime.identity_authority.issue_credential(
            uri=uri,
            credential_id="cred.b",
            actor="authority://root",
            policy_version="v1",
        )

    runtime.identity_authority.issue_credential(
        uri=uri,
        credential_id="cred.c",
        actor="authority://root",
        policy_version="v2",
    )
    state = runtime.state_engine.rebuild_identity_state(uri)
    assert state["credential_refs"]["cred.c"]["status"] == "active"

