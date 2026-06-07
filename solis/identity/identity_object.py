from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from solis.services.qso_bridge import QSOBridge


@dataclass
class IrisIdentityObject:
    iris_hash: str
    pq_public_key: str
    recovery_policy: dict[str, Any]
    device_registry: list[str] = field(default_factory=list)
    consent_ledger: list[dict[str, Any]] = field(default_factory=list)

    @property
    def uri(self) -> str:
        return f"qso://identity.iris.{self.iris_hash}"

    def to_state(self) -> Dict[str, Any]:
        return {
            "iris_hash": self.iris_hash,
            "pq_public_key": self.pq_public_key,
            "recovery_policy": dict(self.recovery_policy),
            "device_registry": list(self.device_registry),
            "consent_ledger": list(self.consent_ledger),
        }


class IdentityService:
    def __init__(self, qso: QSOBridge | None = None) -> None:
        self.qso = qso or QSOBridge()

    def create_identity(self, identity: IrisIdentityObject, *, actor: str = "identity.bootstrap") -> dict[str, Any]:
        if not self.qso.has(identity.uri):
            self.qso.create(identity.uri, {"type": "iris_identity", "version": "v1"})

        return self.qso.patch(
            identity.uri,
            identity.to_state(),
            actor=actor,
            policy_version="v1",
            node_id="identity",
        )

    def record_consent(
        self,
        *,
        iris_hash: str,
        consent_type: str,
        granted: bool,
        actor: str = "identity.consent",
    ) -> dict[str, Any]:
        uri = f"qso://identity.iris.{iris_hash}"
        obj = self.qso.read(uri)
        current = obj.get("state_layer", {})
        ledger = list(current.get("consent_ledger", []))
        ledger.append({"consent_type": consent_type, "granted": bool(granted)})

        return self.qso.patch(
            uri,
            {"consent_ledger": ledger},
            actor=actor,
            policy_version="v1",
            node_id="identity",
        )
