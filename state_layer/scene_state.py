from __future__ import annotations

from typing import Dict


class SceneState:
    def __init__(self) -> None:
        self.objects: Dict[str, Dict[str, str]] = {}

    def update_object(self, obj_id: str, properties: Dict[str, str]) -> None:
        self.objects[obj_id] = properties

    def read_scene(self) -> Dict[str, Dict[str, str]]:
        return dict(self.objects)
