from __future__ import annotations

import time
from urllib.request import Request, urlopen

from services.transport.adapters.base import BaseTransport
from services.transport.models import TransportMode, TransportRequest, TransportResponse


class DirectAdapter(BaseTransport):
    mode = TransportMode.DIRECT
    name = "direct"

    def send(self, request: TransportRequest) -> TransportResponse:
        if request.url.startswith("mock://"):
            return self._mock_response(request, mode=self.mode, adapter=self.name)

        started = time.perf_counter()
        req = Request(
            url=request.url,
            data=request.body or None,
            headers=request.headers,
            method=request.method,
        )
        with urlopen(req, timeout=request.timeout_seconds) as resp:
            body = resp.read()
            headers = {str(k).lower(): str(v) for k, v in resp.headers.items()}
            elapsed = (time.perf_counter() - started) * 1000.0
            return TransportResponse(
                status_code=int(resp.status),
                headers=headers,
                body=body,
                elapsed_ms=elapsed,
                mode=self.mode,
                adapter=self.name,
            )
