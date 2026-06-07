from __future__ import annotations

from typing import Dict, List

from qso_runtime.qso_object import QSO


class QSORegistry:
    def __init__(self) -> None:
        self._objects: Dict[str, QSO] = {}

    def register_qso(self, qso: QSO) -> QSO:
        if qso.uri in self._objects:
            raise ValueError(f"QSO already exists: {qso.uri}")
        self._objects[qso.uri] = qso
        return qso

    def get_qso(self, uri: str) -> QSO:
        return self._objects[uri]

    def list_qsos(self) -> List[str]:
        return sorted(self._objects)
