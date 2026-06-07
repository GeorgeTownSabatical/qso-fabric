from __future__ import annotations

from typing import Any, AsyncIterator, Dict, cast

from api.mcp_tools.qso_tools import QSOMCPTools


class QSOBridge:
    """Stable qso.* adapter so Solis code does not depend on fabric internals."""

    def __init__(self, tools: QSOMCPTools | None = None) -> None:
        self.tools = tools or QSOMCPTools()

    def create(self, uri: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        return cast(Dict[str, Any], self.tools.qso_create(uri, schema))

    def read(self, uri: str) -> Dict[str, Any]:
        return cast(Dict[str, Any], self.tools.qso_read(uri))

    def patch(self, uri: str, delta: Dict[str, Any], *, actor: str, policy_version: str, node_id: str) -> Dict[str, Any]:
        return cast(
            Dict[str, Any],
            self.tools.qso_patch(uri=uri, delta=delta, actor=actor, policy_version=policy_version, node_id=node_id),
        )

    def timeline(self, uri: str, strict: bool = True) -> list[Dict[str, Any]]:
        return cast(list[Dict[str, Any]], self.tools.qso_timeline(uri, strict=strict))

    def entangle(self, uri_a: str, uri_b: str, relationship: str) -> Dict[str, Any]:
        return cast(Dict[str, Any], self.tools.qso_entangle(uri_a, uri_b, relationship, bidirectional=False))

    def subscribe(self, uri_pattern: str) -> AsyncIterator[Dict[str, Any]]:
        if uri_pattern.endswith("*"):
            return cast(AsyncIterator[Dict[str, Any]], self.tools.qso_subscribe_prefix(uri_pattern[:-1]))
        return cast(AsyncIterator[Dict[str, Any]], self.tools.qso_subscribe(uri_pattern))

    def has(self, uri: str) -> bool:
        return cast(bool, self.tools.runtime.registry.has(uri))

    def sign(self, payload: str) -> str:
        return cast(str, self.tools.runtime.crypto.sign(payload))
