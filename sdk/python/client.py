from __future__ import annotations

from typing import Any, Dict

from api.mcp_tools.qso_tools import QSOMCPTools


class QSOClient:
    def __init__(self, tools: QSOMCPTools | None = None) -> None:
        self.tools = tools or QSOMCPTools()

    def create(self, uri: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        return self.tools.qso_create(uri, schema)

    def read(self, uri: str) -> Dict[str, Any]:
        return self.tools.qso_read(uri)

    def patch(self, uri: str, delta: Dict[str, Any], actor: str = "client") -> Dict[str, Any]:
        return self.tools.qso_patch(uri, delta, actor=actor)
