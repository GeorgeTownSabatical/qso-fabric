from __future__ import annotations

from typing import Dict


class GlobalRegistryService:
    def __init__(self) -> None:
        self._nodes: Dict[str, Dict[str, str | float]] = {}

    def register(self, node_id: str, metadata: Dict[str, str | float]) -> None:
        self._nodes[node_id] = dict(metadata)

    def list_nodes(self) -> Dict[str, Dict[str, str | float]]:
        return dict(self._nodes)
