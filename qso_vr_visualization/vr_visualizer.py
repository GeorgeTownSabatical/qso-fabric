from __future__ import annotations

from typing import Any, Dict, List

class QSO3DVisualizer:
    def __init__(self) -> None:
        self._uris: List[str] = []
        self.running = False
        self.scene_updates: List[Dict[str, Any]] = []

    def subscribe(self, uris: list[str]) -> None:
        self._uris = sorted(set(str(uri) for uri in uris))

    def start(self, update_interval: float = 0.5) -> None:
        _ = update_interval
        self.running = True

    def stop(self) -> None:
        self.running = False

    def ingest_projection(self, projection: Dict[str, Any]) -> Dict[str, Any]:
        uri = str(projection.get("uri", ""))
        if self._uris and uri not in self._uris:
            return {}
        update = {
            "uri": uri,
            "spatial": projection.get("render_delta", {}).get("spatial", {}),
            "objects": projection.get("render_delta", {}).get("objects", []),
            "meta": projection.get("meta", {}),
        }
        self.scene_updates.append(update)
        return update
