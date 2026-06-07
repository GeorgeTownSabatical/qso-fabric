from __future__ import annotations

from pathlib import Path

from sandbox_mcp import SandboxMCPServer


def test_sandbox_mcp_server_compat_wrapper(tmp_path: Path) -> None:
    server = SandboxMCPServer(state_root=tmp_path / "sandboxes")
    sandbox = server.create_sandbox("compat-session")
    sid = sandbox["sandbox_id"]

    created = server.qso_create(sid, "qso://demo.compat", {"type": "object"})
    assert created["action"] == "create"
    assert created["result"]["uri"].startswith(f"qso://sandbox/{sid}/")
