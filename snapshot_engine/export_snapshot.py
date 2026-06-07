from __future__ import annotations

from api.mcp_tools.qso_tools import QSOMCPTools


class SnapshotExporter:
    def __init__(self, tools: QSOMCPTools) -> None:
        self.tools = tools

    def export_qff(self, qso_uri: str, path: str) -> None:
        blob = self.tools.qso_export_snapshot(qso_uri)
        with open(path, "wb") as f:
            f.write(blob)
