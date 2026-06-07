from __future__ import annotations

from typing import Any, Dict, List

class QSOVisualizer:
    def __init__(self) -> None:
        self._uris: List[str] = []
        self.running = False
        self.frames: List[Dict[str, Any]] = []

    def subscribe(self, uris: list[str]) -> None:
        self._uris = sorted(set(str(uri) for uri in uris))

    def start(self, update_interval: float = 0.5) -> None:
        _ = update_interval
        self.running = True

    def stop(self) -> None:
        self.running = False

    def ingest(self, uri: str, state: Dict[str, Any]) -> Dict[str, Any]:
        if self._uris and uri not in self._uris:
            return {}
        frame = {"uri": uri, "state_keys": sorted(state), "state": dict(state)}
        self.frames.append(frame)
        return frame
