from __future__ import annotations

from typing import Dict


class AccessControl:
    def __init__(self) -> None:
        self.policies: Dict[str, Dict[str, list[str]]] = {}

    def set_policy(self, uri: str, policy: Dict[str, list[str]]) -> None:
        self.policies[uri] = policy

    def check_read(self, uri: str, actor: str) -> bool:
        return actor in self.policies.get(uri, {}).get("read", [actor])

    def check_write(self, uri: str, actor: str) -> bool:
        return actor in self.policies.get(uri, {}).get("write", [actor])
