from __future__ import annotations

from copy import deepcopy
from typing import Dict

from api.schemas.models import QSOObject


class RegistryService:
    def __init__(self) -> None:
        self._objects: Dict[str, QSOObject] = {}

    def create(self, obj: QSOObject) -> QSOObject:
        if obj.uri in self._objects:
            raise ValueError(f"QSO already exists: {obj.uri}")
        self._objects[obj.uri] = obj
        return deepcopy(obj)

    def read(self, uri: str) -> QSOObject:
        if uri not in self._objects:
            raise KeyError(f"QSO not found: {uri}")
        return deepcopy(self._objects[uri])

    def update(self, obj: QSOObject) -> None:
        if obj.uri not in self._objects:
            raise KeyError(f"QSO not found: {obj.uri}")
        self._objects[obj.uri] = obj

    def has(self, uri: str) -> bool:
        return uri in self._objects

    def list_uris(self) -> list[str]:
        return sorted(self._objects)
