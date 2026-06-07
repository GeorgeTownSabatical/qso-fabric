from __future__ import annotations

from api.mcp_tools.qso_tools import QSOMCPTools


class SnapshotImporter:
    def __init__(self, tools: QSOMCPTools) -> None:
        self.tools = tools

    def import_qff(self, qff_file: str):
        with open(qff_file, "rb") as f:
            blob = f.read()
        return self.tools.qso_import_snapshot(blob)
