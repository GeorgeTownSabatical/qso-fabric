from __future__ import annotations

from typing import Any, Dict

from api.mcp_tools.qso_tools import QSOMCPTools


class QSOTools:
    def __init__(self, tools: QSOMCPTools | None = None) -> None:
        self._tools = tools or QSOMCPTools()

    def create(self, uri: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        return self._tools.qso_create(uri, schema)

    def read(self, uri: str) -> Dict[str, Any]:
        return self._tools.qso_read(uri)

    def patch(self, uri: str, delta: Dict[str, Any], actor: str = "agent") -> Dict[str, Any]:
        return self._tools.qso_patch(uri, delta, actor=actor)

    def export(self, uri: str) -> bytes:
        return self._tools.qso_export_snapshot(uri)

    def import_snapshot(self, qff: bytes) -> Dict[str, Any]:
        return self._tools.qso_import_snapshot(qff)

    def entangle(self, uri_a: str, uri_b: str, relationship: str) -> Dict[str, Any]:
        return self._tools.qso_entangle(uri_a, uri_b, relationship)

    def transport_set(self, mode: str, actor: str = "agent", policy_version: str = "v1", node_id: str = "local") -> Dict[str, Any]:
        return self._tools.qso_transport_set(mode=mode, actor=actor, policy_version=policy_version, node_id=node_id)

    def transport_status(self) -> Dict[str, Any]:
        return self._tools.qso_transport_status()

    def transport_health(self) -> Dict[str, Any]:
        return self._tools.qso_transport_health()

    def transport_policy(self) -> Dict[str, Any]:
        return self._tools.qso_transport_policy()

    def quantum_create(self, uri: str, payload: Dict[str, Any], actor: str = "agent", policy_version: str = "v1", node_id: str = "local") -> Dict[str, Any]:
        return self._tools.qso_quantum_create(
            uri=uri,
            payload=payload,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def quantum_execute(self, uri: str, actor: str = "agent", policy_version: str = "v1", node_id: str = "local") -> Dict[str, Any]:
        return self._tools.qso_quantum_execute(uri=uri, actor=actor, policy_version=policy_version, node_id=node_id)

    def quantum_replay(self, uri: str, strict: bool = True) -> Dict[str, Any]:
        return self._tools.qso_quantum_replay(uri=uri, strict=strict)

    def quantum_lisp_compile(self, source: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return self._tools.qso_quantum_lisp_compile(source=source, metadata=metadata or {})

    def quantum_lisp_analyze(self, uri: str, actor: str = "agent", policy_version: str = "v1", node_id: str = "local") -> Dict[str, Any]:
        return self._tools.qso_quantum_lisp_analyze(uri=uri, actor=actor, policy_version=policy_version, node_id=node_id)

    def quantum_lisp_replay(self, uri: str, strict: bool = True) -> Dict[str, Any]:
        return self._tools.qso_quantum_lisp_replay(uri=uri, strict=strict)
