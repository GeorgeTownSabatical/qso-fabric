from api.mcp_tools.qso_tools import QSOMCPTools
from mcp_server.server_core import MCPServer
from tools.qso_controller import QSOController


def test_server_and_controller_smoke() -> None:
    server = MCPServer()
    server.start()

    controller = QSOController(server.tools)
    uri = "qso://identity.user.hash"
    controller.create(uri, {"type": "identity"})
    controller.patch(uri, {"active": True}, actor="tester")

    assert uri in server.list_resources()

    state = controller.read(uri)
    assert state["state_layer"]["active"] is True

    server.stop()


def test_snapshot_roundtrip_via_tools() -> None:
    tools = QSOMCPTools()
    uri = "qso://simulation.checkpoint"
    tools.qso_create(uri, {"type": "simulation"})
    tools.qso_patch(uri, {"epoch": 1}, actor="trainer")

    blob = tools.qso_export_snapshot(uri)
    data = tools.qso_import_snapshot(blob)
    assert data["header"]["uri"] == uri
