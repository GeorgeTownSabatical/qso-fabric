from __future__ import annotations

import time
from urllib.request import Request, urlopen

from services.transport.adapters.base import BaseTransport
from services.transport.models import TransportMode, TransportRequest, TransportResponse


class VPNAdapter(BaseTransport):
    mode = TransportMode.VPN
    name = "vpn"

    def __init__(self, interface: str | None = None) -> None:
        self.interface = interface or "system-default"

    def send(self, request: TransportRequest) -> TransportResponse:
        if request.url.startswith("mock://"):
            mocked = self._mock_response(request, mode=self.mode, adapter=self.name)
            mocked.headers["x-qso-vpn-interface"] = self.interface
            return mocked

        started = time.perf_counter()
        headers = dict(request.headers)
        headers["X-QSO-VPN-Interface"] = self.interface
        req = Request(
            url=request.url,
            data=request.body or None,
            headers=headers,
            method=request.method,
        )
        with urlopen(req, timeout=request.timeout_seconds) as resp:
            body = resp.read()
            response_headers = {str(k).lower(): str(v) for k, v in resp.headers.items()}
            response_headers["x-qso-vpn-interface"] = self.interface
            elapsed = (time.perf_counter() - started) * 1000.0
            return TransportResponse(
                status_code=int(resp.status),
                headers=response_headers,
                body=body,
                elapsed_ms=elapsed,
                mode=self.mode,
                adapter=self.name,
            )
