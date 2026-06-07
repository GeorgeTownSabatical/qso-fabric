from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class QSO:
    uri: str
    schema_def: Dict[str, Any]
    state: Dict[str, Any] = field(default_factory=dict)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    entanglements: List[Dict[str, Any]] = field(default_factory=list)

    def apply(self, delta: Dict[str, Any]) -> None:
        self.state.update(delta)
