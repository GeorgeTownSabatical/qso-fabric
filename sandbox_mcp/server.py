from __future__ import annotations

from mcp_qso_edu.server import QSOEduMCPServer


class SandboxMCPServer(QSOEduMCPServer):
    """Compatibility wrapper that exposes the naming used in the design doc."""


__all__ = ["SandboxMCPServer"]
