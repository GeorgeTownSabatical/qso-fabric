from __future__ import annotations

from enum import Enum


class IdentityEventType(str, Enum):
    IDENTITY_CREATE = "IDENTITY_CREATE"
    KEY_ROTATE = "KEY_ROTATE"
    CREDENTIAL_ISSUE = "CREDENTIAL_ISSUE"
    CREDENTIAL_REVOKE = "CREDENTIAL_REVOKE"
    ENTITLEMENT_GRANT = "ENTITLEMENT_GRANT"
    ENTITLEMENT_REVOKE = "ENTITLEMENT_REVOKE"
    LINK_ATTACH = "LINK_ATTACH"
    LINK_REVOKE = "LINK_REVOKE"
    MEASURE_VERIFY = "MEASURE_VERIFY"
    IDENTITY_FREEZE = "IDENTITY_FREEZE"
    IDENTITY_ARCHIVE = "IDENTITY_ARCHIVE"


# Frozen canonical order for deterministic pipelines.
CANONICAL_IDENTITY_EVENT_SEQUENCE: tuple[IdentityEventType, ...] = (
    IdentityEventType.IDENTITY_CREATE,
    IdentityEventType.KEY_ROTATE,
    IdentityEventType.CREDENTIAL_ISSUE,
    IdentityEventType.CREDENTIAL_REVOKE,
    IdentityEventType.ENTITLEMENT_GRANT,
    IdentityEventType.ENTITLEMENT_REVOKE,
    IdentityEventType.LINK_ATTACH,
    IdentityEventType.LINK_REVOKE,
    IdentityEventType.MEASURE_VERIFY,
    IdentityEventType.IDENTITY_FREEZE,
    IdentityEventType.IDENTITY_ARCHIVE,
)


# Minimal payload contract used by the kernel reducer.
IDENTITY_EVENT_SCHEMA: dict[IdentityEventType, tuple[str, ...]] = {
    IdentityEventType.IDENTITY_CREATE: ("immutable_core",),
    IdentityEventType.KEY_ROTATE: ("key_ref",),
    IdentityEventType.CREDENTIAL_ISSUE: ("credential_id",),
    IdentityEventType.CREDENTIAL_REVOKE: ("credential_id",),
    IdentityEventType.ENTITLEMENT_GRANT: ("entitlement_id",),
    IdentityEventType.ENTITLEMENT_REVOKE: ("entitlement_id",),
    IdentityEventType.LINK_ATTACH: ("link_id", "target_uri", "relationship"),
    IdentityEventType.LINK_REVOKE: ("link_id",),
    IdentityEventType.MEASURE_VERIFY: ("measurement_id",),
    IdentityEventType.IDENTITY_FREEZE: tuple(),
    IdentityEventType.IDENTITY_ARCHIVE: tuple(),
}


def parse_identity_event_type(value: str | IdentityEventType) -> IdentityEventType:
    if isinstance(value, IdentityEventType):
        return value
    return IdentityEventType(str(value))

