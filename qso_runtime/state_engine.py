from __future__ import annotations

from typing import Any, Dict

from qso_runtime.qso_registry import QSORegistry


class StateEngine:
    def __init__(self, registry: QSORegistry) -> None:
        self.registry = registry

    def read_state(self, uri: str) -> Dict[str, Any]:
        return dict(self.registry.get_qso(uri).state)

    def write_state(self, uri: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        qso = self.registry.get_qso(uri)
        qso.apply(patch)
        return dict(qso.state)
