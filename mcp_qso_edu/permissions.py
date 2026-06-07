from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Capability(str, Enum):
    CREATE = "CAP_CREATE"
    READ = "CAP_READ"
    PATCH = "CAP_PATCH"
    TIMELINE = "CAP_TIMELINE"
    ENTANGLE = "CAP_ENTANGLE"
    EXPORT = "CAP_EXPORT"
    SUBSCRIBE = "CAP_SUBSCRIBE"


DEFAULT_CAPABILITIES: set[Capability] = {
    Capability.CREATE,
    Capability.READ,
    Capability.PATCH,
    Capability.TIMELINE,
    Capability.ENTANGLE,
    Capability.EXPORT,
    Capability.SUBSCRIBE,
}


PERMISSIONS: dict[str, set[str]] = {
    "system": {"append", "summarize", "fork"},
    "assistant": {"append", "summarize"},
    "agent": {"append"},
    "user": {"append"},
}


@dataclass(slots=True)
class PermissionSet:
    capabilities: set[Capability]

    @classmethod
    def default(cls) -> "PermissionSet":
        return cls(capabilities=set(DEFAULT_CAPABILITIES))

    @classmethod
    def from_values(cls, values: Iterable[str]) -> "PermissionSet":
        caps: set[Capability] = set()
        for value in values:
            normalized = str(value).strip().upper()
            caps.add(Capability(normalized))
        return cls(capabilities=caps)

    def require(self, capability: Capability) -> None:
        if capability not in self.capabilities:
            raise PermissionError(f"sandbox capability not granted: {capability.value}")


def require_action(role: str, action: str) -> None:
    normalized_role = str(role).strip()
    normalized_action = str(action).strip()
    allowed = PERMISSIONS.get(normalized_role, set())
    if normalized_action not in allowed:
        raise PermissionError(f"{normalized_role} not permitted to {normalized_action}")
