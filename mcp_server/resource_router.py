from __future__ import annotations

from typing import Dict


class ResourceRouter:
    def resolve_uri(self, uri: str) -> str:
        if not uri.startswith("qso://"):
            raise ValueError(f"unsupported URI scheme: {uri}")
        return uri

    def route_request(self, request: Dict[str, object]) -> Dict[str, object]:
        if "uri" in request:
            request = dict(request)
            request["uri"] = self.resolve_uri(str(request["uri"]))
        return request
