from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Dict, List


class EntanglementEngine:
    def __init__(self) -> None:
        self.links: DefaultDict[str, List[Dict[str, str | float | int]]] = defaultdict(list)

    def entangle(self, uri_a: str, uri_b: str, relationship: str, sync_mode: str = "push") -> None:
        self.links[uri_a].append({"target": uri_b, "relationship": relationship, "sync_mode": sync_mode})

    def remove_entanglement(self, uri_a: str, uri_b: str) -> None:
        self.links[uri_a] = [link for link in self.links[uri_a] if link["target"] != uri_b]

    def get_entanglements(self, uri: str) -> List[Dict[str, str | float | int]]:
        return list(self.links.get(uri, []))
