from __future__ import annotations

from typing import Any, Dict

from api.mcp_tools.qso_tools import QSOMCPTools


class QSOController:
    def __init__(self, tools: QSOMCPTools | None = None) -> None:
        self.tools = tools or QSOMCPTools()

    def create(self, uri: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        return self.tools.qso_create(uri, schema)

    def read(self, uri: str) -> Dict[str, Any]:
        return self.tools.qso_read(uri)

    def patch(self, uri: str, delta: Dict[str, Any], actor: str = "agent") -> Dict[str, Any]:
        return self.tools.qso_patch(uri, delta, actor=actor)

    def transport_set(self, mode: str, actor: str = "agent", policy_version: str = "v1", node_id: str = "local") -> Dict[str, Any]:
        return self.tools.qso_transport_set(mode=mode, actor=actor, policy_version=policy_version, node_id=node_id)

    def transport_status(self) -> Dict[str, Any]:
        return self.tools.qso_transport_status()

    def quantum_create(
        self,
        uri: str,
        payload: Dict[str, Any],
        actor: str = "agent",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        return self.tools.qso_quantum_create(
            uri=uri,
            payload=payload,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def quantum_execute(self, uri: str, actor: str = "agent", policy_version: str = "v1", node_id: str = "local") -> Dict[str, Any]:
        return self.tools.qso_quantum_execute(uri=uri, actor=actor, policy_version=policy_version, node_id=node_id)
