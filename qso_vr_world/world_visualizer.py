from __future__ import annotations

from typing import Any, Dict, List

class VRWorldVisualizer:
    def __init__(self) -> None:
        self._uris: List[str] = []
        self.running = False
        self.world_state: Dict[str, Dict[str, Any]] = {}

    def subscribe(self, qso_uris: list[str]) -> None:
        self._uris = sorted(set(str(uri) for uri in qso_uris))

    def start(self, update_interval: float = 0.5) -> None:
        _ = update_interval
        self.running = True

    def stop(self) -> None:
        self.running = False

    def apply_patch(self, uri: str, delta: Dict[str, Any]) -> Dict[str, Any]:
        if self._uris and uri not in self._uris:
            return {}
        current = dict(self.world_state.get(uri, {}))
        current.update(delta)
        self.world_state[uri] = current
        return {"uri": uri, "state": current}
