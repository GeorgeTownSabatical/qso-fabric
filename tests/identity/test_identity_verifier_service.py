from __future__ import annotations

from copy import deepcopy

from services.runtime import QSOFabricRuntime


def test_verifier_accepts_valid_bundle() -> None:
    runtime = QSOFabricRuntime()
    uri = "qso://identity.person.verifier_001"

    runtime.identity_authority.create_identity(
        uri=uri,
        immutable_core={"subject_ref": "verifier_001"},
        actor="authority://root",
        policy_version="v1",
    )
    runtime.identity_authority.issue_credential(
        uri=uri,
        credential_id="cred.alpha",
        credential_body={"scope": "alpha"},
        actor="authority://root",
        policy_version="v1",
    )

    bundle = runtime.identity_verifier.export_bundle(uri=uri, trust_roots=["trust://root"])
    result = runtime.identity_verifier.verify_bundle(bundle)
    assert result["accepted"] is True
    assert [step["step"] for step in result["steps"]] == [
        "validate_block_hashes",
        "validate_signatures",
        "validate_policy_version",
        "validate_revocation_status",
        "deterministic_replay",
        "compare_state_hash",
    ]


def test_verifier_rejects_block_manifest_mismatch() -> None:
    runtime = QSOFabricRuntime()
    uri = "qso://identity.person.verifier_002"

    runtime.identity_authority.create_identity(
        uri=uri,
        immutable_core={"subject_ref": "verifier_002"},
        actor="authority://root",
        policy_version="v1",
    )
    bundle = runtime.identity_verifier.export_bundle(uri=uri)

    tampered = deepcopy(bundle)
    tampered["block_manifest"]["header.json"] = "00" * 32
    tampered = runtime.identity_verifier.sign_bundle(tampered)

    result = runtime.identity_verifier.verify_bundle(tampered)
    assert result["accepted"] is False
    assert result["failed_step"] == "validate_block_hashes"


def test_verifier_rejects_tampered_event_signature() -> None:
    runtime = QSOFabricRuntime()
    uri = "qso://identity.person.verifier_003"

    runtime.identity_authority.create_identity(
        uri=uri,
        immutable_core={"subject_ref": "verifier_003"},
        actor="authority://root",
        policy_version="v1",
    )
    runtime.identity_authority.issue_credential(
        uri=uri,
        credential_id="cred.beta",
        credential_body={"scope": "beta"},
        actor="authority://root",
        policy_version="v1",
    )

    bundle = runtime.identity_verifier.export_bundle(uri=uri)
    tampered = deepcopy(bundle)
    tampered["timeline"][0]["signature"] = "invalid-signature"
    tampered = runtime.identity_verifier.sign_bundle(tampered)

    result = runtime.identity_verifier.verify_bundle(tampered)
    assert result["accepted"] is False
    assert result["failed_step"] == "validate_signatures"


def test_verifier_archived_policy_gate() -> None:
    runtime = QSOFabricRuntime()
    uri = "qso://identity.person.verifier_004"

    runtime.identity_authority.create_identity(
        uri=uri,
        immutable_core={"subject_ref": "verifier_004"},
        actor="authority://root",
        policy_version="v1",
    )
    runtime.identity_authority.archive_identity(
        uri=uri,
        reason="retired",
        actor="authority://root",
        policy_version="v1",
    )

    bundle = runtime.identity_verifier.export_bundle(uri=uri)

    rejected = runtime.identity_verifier.verify_bundle(bundle, reject_archived=True)
    assert rejected["accepted"] is False
    assert rejected["failed_step"] == "validate_revocation_status"

    allowed = runtime.identity_verifier.verify_bundle(bundle, reject_archived=False)
    assert allowed["accepted"] is True

