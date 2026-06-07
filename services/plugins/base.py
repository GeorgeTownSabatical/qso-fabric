from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol


@dataclass(frozen=True)
class DemoNodeSpec:
    uri: str
    state: Dict[str, Any]


class DemoPlugin(Protocol):
    plugin_id: str

    def manifest(self) -> Dict[str, Any]:
        ...

    def nodes(self, *, world_uri: str) -> List[DemoNodeSpec]:
        ...

    def animations(self, *, world_uri: str) -> List[Dict[str, Any]]:
        ...
