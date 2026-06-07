"""Entity and relationship data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


@dataclass(slots=True)
class Entity:
    name: str
    type: str
    aliases: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    id: str | None = None

    def __post_init__(self) -> None:
        if self.id is None:
            self.id = _stable_id(self.type.lower(), self.name.lower())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Relationship:
    source_id: str
    target_id: str
    type: str
    attributes: dict[str, Any] = field(default_factory=dict)
    from_ts: str | None = None
    to_ts: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Event:
    kind: str
    payload: dict[str, Any]
    ts: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
