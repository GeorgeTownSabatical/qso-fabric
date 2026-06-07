"""GIS lookup agent."""

from __future__ import annotations

from core.oc_clients import MockGISClient


class GISAgent:
    def __init__(self):
        self.client = MockGISClient()

    def get_geometry(self, apn: str) -> dict:
        return self.client.get_geometry(apn)

    def get_neighbors(self, apn: str) -> list[str]:
        return list(self.get_geometry(apn).get("neighbors", []))
