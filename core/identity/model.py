from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from core.identity.events import IdentityEventType


class IdentityLifecycleStatus(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    ARCHIVED = "archived"


class IdentityLinkStatus(str, Enum):
    ACTIVE = "active"
    INERT = "inert"


class IdentityLinkRelationship(str, Enum):
    ORGANIZATION_MEMBERSHIP = "organization_membership"
    DEVICE_BINDING = "device_binding"
    CREDENTIAL_LINKAGE = "credential_linkage"
    ROLE_ASSIGNMENT = "role_assignment"
    MULTISIG_RELATIONSHIP = "multisig_relationship"
    GUARDIAN_RELATIONSHIP = "guardian_relationship"
    HARDWARE_ANCHOR_BINDING = "hardware_anchor_binding"


@dataclass(frozen=True)
class IdentityKernelEvent:
    event_id: str
    event_type: IdentityEventType
    actor: str
    policy_version: str
    payload: Dict[str, Any]
    node_id: str = "local"
    timestamp: str | None = None

