from __future__ import annotations

from typing import List, Tuple


class EntanglementNode:
    def __init__(self, uri: str) -> None:
        self.uri = uri
        self.links: List[Tuple[str, str, str]] = []

    def add_link(self, other_uri: str, relationship: str, sync_mode: str) -> None:
        self.links.append((other_uri, relationship, sync_mode))

    def remove_link(self, other_uri: str) -> None:
        self.links = [link for link in self.links if link[0] != other_uri]

    def list_links(self) -> List[Tuple[str, str, str]]:
        return list(self.links)
