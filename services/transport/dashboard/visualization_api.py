from __future__ import annotations

from typing import Any

from services.transport.circuit_registry import CircuitRegistry
from services.transport.transport_manager import TransportManager


class TransportVisualizationAPI:
    def __init__(self, manager: TransportManager, circuits: CircuitRegistry) -> None:
        self.manager = manager
        self.circuits = circuits

    def snapshot(self) -> dict[str, Any]:
        return {
            "transport": self.manager.status(),
            "health": self.manager.health(),
            "policy": self.manager.policy(),
            "metrics": self.manager.metrics(),
            "circuits": self.circuits.list(),
        }

    def mesh_payload(self) -> dict[str, Any]:
        state = self.manager.status()
        mode = str(state.get("mode", "direct"))
        nodes = [
            {"id": state.get("node_id", "local"), "kind": "qso-node", "mode": mode},
            {"id": f"transport-{mode}", "kind": "transport", "mode": mode},
        ]
        edges = [
            {
                "source": state.get("node_id", "local"),
                "target": f"transport-{mode}",
                "label": "active_transport",
            }
        ]
        return {"nodes": nodes, "edges": edges}
