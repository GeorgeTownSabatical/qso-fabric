from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from api.schemas.models import QSOEvent
from core.identity.events import IdentityEventType
from services.state_engine.service import StateEngineService


class IdentityAuthorityService:
    """Authority-side identity operations built on deterministic identity events."""

    def __init__(self, state_engine: StateEngineService, policy_sync: Any) -> None:
        self.state_engine = state_engine
        self.policy_sync = policy_sync

    def create_identity(
        self,
        uri: str,
        immutable_core: Dict[str, Any],
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> QSOEvent:
        return self.state_engine.create_identity(
            uri=uri,
            immutable_core=deepcopy(immutable_core),
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def issue_credential(
        self,
        uri: str,
        credential_id: str,
        credential_body: Dict[str, Any] | None = None,
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> QSOEvent:
        payload = {"credential_id": credential_id}
        if credential_body:
            payload["credential_body"] = deepcopy(credential_body)
        return self.state_engine.apply_identity_event(
            uri=uri,
            event_type=IdentityEventType.CREDENTIAL_ISSUE,
            payload=payload,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def revoke_credential(
        self,
        uri: str,
        credential_id: str,
        reason: str,
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> QSOEvent:
        return self.state_engine.apply_identity_event(
            uri=uri,
            event_type=IdentityEventType.CREDENTIAL_REVOKE,
            payload={"credential_id": credential_id, "reason": reason},
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def rotate_key(
        self,
        uri: str,
        key_ref: str,
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> QSOEvent:
        return self.state_engine.apply_identity_event(
            uri=uri,
            event_type=IdentityEventType.KEY_ROTATE,
            payload={"key_ref": key_ref},
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def grant_entitlement(
        self,
        uri: str,
        entitlement_id: str,
        entitlement_body: Dict[str, Any] | None = None,
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> QSOEvent:
        payload = {"entitlement_id": entitlement_id}
        if entitlement_body:
            payload["entitlement_body"] = deepcopy(entitlement_body)
        return self.state_engine.apply_identity_event(
            uri=uri,
            event_type=IdentityEventType.ENTITLEMENT_GRANT,
            payload=payload,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def revoke_entitlement(
        self,
        uri: str,
        entitlement_id: str,
        reason: str | None = None,
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> QSOEvent:
        payload: Dict[str, Any] = {"entitlement_id": entitlement_id}
        if reason:
            payload["reason"] = reason
        return self.state_engine.apply_identity_event(
            uri=uri,
            event_type=IdentityEventType.ENTITLEMENT_REVOKE,
            payload=payload,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def attach_link(
        self,
        uri: str,
        link_id: str,
        target_uri: str,
        relationship: str,
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> QSOEvent:
        return self.state_engine.apply_identity_event(
            uri=uri,
            event_type=IdentityEventType.LINK_ATTACH,
            payload={
                "link_id": link_id,
                "target_uri": target_uri,
                "relationship": relationship,
            },
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def revoke_link(
        self,
        uri: str,
        link_id: str,
        reason: str | None = None,
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> QSOEvent:
        payload: Dict[str, Any] = {"link_id": link_id}
        if reason:
            payload["reason"] = reason
        return self.state_engine.apply_identity_event(
            uri=uri,
            event_type=IdentityEventType.LINK_REVOKE,
            payload=payload,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def freeze_identity(
        self,
        uri: str,
        reason: str,
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> QSOEvent:
        return self.state_engine.apply_identity_event(
            uri=uri,
            event_type=IdentityEventType.IDENTITY_FREEZE,
            payload={"reason": reason},
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def archive_identity(
        self,
        uri: str,
        reason: str,
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> QSOEvent:
        return self.state_engine.apply_identity_event(
            uri=uri,
            event_type=IdentityEventType.IDENTITY_ARCHIVE,
            payload={"reason": reason},
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def publish_policy(self, policy: Dict[str, Any], actor: str = "authority", node_id: str = "local") -> Dict[str, Any]:
        return self.policy_sync.publish(deepcopy(policy), actor=actor, node_id=node_id)

    def current_policy(self) -> Dict[str, Any]:
        return self.policy_sync.current()

