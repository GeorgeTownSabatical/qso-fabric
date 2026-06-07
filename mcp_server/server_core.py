from __future__ import annotations

from api.mcp_tools.qso_tools import QSOMCPTools


class MCPServer:
    def __init__(self) -> None:
        self.tools = QSOMCPTools()
        self.running = False

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def list_resources(self) -> list[str]:
        return self.tools.runtime.registry.list_uris()
