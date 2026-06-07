from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, DefaultDict, List


class VersionControl:
    def __init__(self) -> None:
        self.versions: DefaultDict[str, List[Any]] = defaultdict(list)

    def create_version(self, qso_uri: str, snapshot: Any) -> None:
        self.versions[qso_uri].append(deepcopy(snapshot))

    def rollback(self, qso_uri: str, version_id: int) -> Any:
        return deepcopy(self.versions[qso_uri][version_id])
