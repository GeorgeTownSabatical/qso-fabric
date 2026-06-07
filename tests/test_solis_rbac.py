from __future__ import annotations

from api.rest import QSOIdentityRESTAPI
from solis.governance import RBACAuthorizer, RBACPolicy, extract_actor_role


def test_extract_actor_role_resolution() -> None:
    assert extract_actor_role("dev://alice") == "dev"
    assert extract_actor_role("solis.scheduler") == "system"
    assert extract_actor_role("operator://rest", explicit_role="whale") == "whale"
    assert extract_actor_role("plain-actor", default_role="dev") == "dev"
    assert extract_actor_role("plain-actor", explicit_role="unknown", default_role="whale") == "whale"


def test_rbac_authorizer_default_policy_matrix() -> None:
    authorizer = RBACAuthorizer()

    allow_dev = authorizer.authorize(action="policy.propose", actor="dev://builder")
    assert allow_dev.allowed is True
    assert allow_dev.reason_code == "ROLE_ALLOWED"

    deny_dev = authorizer.authorize(action="policy.activate", actor="dev://builder")
    assert deny_dev.allowed is False
    assert deny_dev.reason_code == "ROLE_NOT_ALLOWED"

    allow_whale = authorizer.authorize(action="policy.activate", actor="whale://approver")
    assert allow_whale.allowed is True
    assert allow_whale.reason_code == "ROLE_ALLOWED"

    allow_system = authorizer.authorize(action="policy.activate", actor="solis.runtime")
    assert allow_system.allowed is True
    assert allow_system.reason_code == "SYSTEM_ACTOR_ALLOW"


def test_rbac_authorizer_unmapped_action_modes() -> None:
    strict = RBACAuthorizer(policy=RBACPolicy(action_roles={}, strict_unmapped_actions=True))
    strict_decision = strict.authorize(action="custom.action", actor="dev://builder")
    assert strict_decision.allowed is False
    assert strict_decision.reason_code == "ACTION_UNMAPPED_DENY"

    permissive = RBACAuthorizer(policy=RBACPolicy(action_roles={}, strict_unmapped_actions=False))
    permissive_decision = permissive.authorize(action="custom.action", actor="dev://builder")
    assert permissive_decision.allowed is True
    assert permissive_decision.reason_code == "ACTION_UNMAPPED_ALLOW"


def test_rest_rbac_allows_dev_policy_propose_and_audits() -> None:
    api = QSOIdentityRESTAPI(
        enforce_rbac=True,
        require_signed_fields=False,
        default_rbac_role="dev",
    )
    status, payload = api.route_post(
        "/v1/policy/propose",
        {
            "policy_body": {"rules": ["allow-demo"]},
            "version": "v2",
            "policy_uri": "qso://solis.policy/v2",
            "actor": "rest-client",
        },
    )

    assert status == 200
    assert payload["event_id"] == "policy_propose:v2"
    assert api._rbac_decision_uris
    audit_uri = api._rbac_decision_uris[-1]
    audit_state = api.tools.qso_read(audit_uri)["state_layer"]
    assert audit_state["action"] == "policy.propose"
    assert audit_state["allowed"] is True
    assert audit_state["role"] == "dev"


def test_rest_rbac_denies_dev_policy_activate_and_returns_audit_uri() -> None:
    api = QSOIdentityRESTAPI(
        enforce_rbac=True,
        require_signed_fields=False,
        default_rbac_role="dev",
    )
    status, payload = api.route_post(
        "/v1/policy/activate",
        {
            "version": "v2",
            "activation_index": 1,
            "policy_uri": "qso://solis.policy/v2",
            "actor": "rest-client",
        },
    )

    assert status == 403
    assert payload["error"] == "rbac_denied"
    assert payload["action"] == "policy.activate"
    assert payload["role"] == "dev"
    assert payload["reason"] == "ROLE_NOT_ALLOWED"
    audit_state = api.tools.qso_read(payload["audit_uri"])["state_layer"]
    assert audit_state["allowed"] is False
    assert audit_state["action"] == "policy.activate"


def test_rest_rbac_allows_whale_policy_activate_with_explicit_role() -> None:
    api = QSOIdentityRESTAPI(
        enforce_rbac=True,
        require_signed_fields=False,
        default_rbac_role="dev",
    )
    status, payload = api.route_post(
        "/v1/policy/activate",
        {
            "version": "v3",
            "activation_index": 2,
            "policy_uri": "qso://solis.policy/v3",
            "actor": "rest-client",
            "role": "whale",
        },
    )

    assert status == 200
    assert payload["event_id"] == "policy_activate:v3:2"
    assert api._rbac_decision_uris
    audit_state = api.tools.qso_read(api._rbac_decision_uris[-1])["state_layer"]
    assert audit_state["allowed"] is True
    assert audit_state["role"] == "whale"
    assert audit_state["action"] == "policy.activate"
