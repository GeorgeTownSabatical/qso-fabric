from __future__ import annotations

from typing import Dict, Optional


class IdentityRegistry:
    def __init__(self) -> None:
        self.identities: Dict[str, Dict[str, str]] = {}

    def register_identity(self, qso_uri: str, identity_data: Dict[str, str]) -> None:
        self.identities[qso_uri] = identity_data

    def lookup_identity(self, qso_uri: str) -> Optional[Dict[str, str]]:
        return self.identities.get(qso_uri)
