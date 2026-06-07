from __future__ import annotations

import hashlib
import time
from urllib.request import ProxyHandler, Request, build_opener

from services.transport.adapters.base import BaseTransport
from services.transport.models import TransportMode, TransportRequest, TransportResponse


class TorAdapter(BaseTransport):
    mode = TransportMode.TOR
    name = "tor"

    def __init__(self, socks_host: str = "127.0.0.1", socks_port: int = 9050) -> None:
        self.socks_host = socks_host
        self.socks_port = int(socks_port)

    def send(self, request: TransportRequest) -> TransportResponse:
        fingerprint = self._exit_fingerprint(request.url)

        if request.url.startswith("mock://"):
            return self._mock_response(
                request,
                mode=self.mode,
                adapter=self.name,
                exit_fingerprint=fingerprint,
            )

        started = time.perf_counter()
        proxy_url = f"socks5h://{self.socks_host}:{self.socks_port}"
        opener = build_opener(ProxyHandler({"http": proxy_url, "https": proxy_url}))
        req = Request(
            url=request.url,
            data=request.body or None,
            headers=request.headers,
            method=request.method,
        )
        try:
            with opener.open(req, timeout=request.timeout_seconds) as resp:
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
                    exit_fingerprint=fingerprint,
                )
        except Exception as exc:  # pragma: no cover - network/host dependent
            elapsed = (time.perf_counter() - started) * 1000.0
            return TransportResponse(
                status_code=599,
                headers={},
                body=b"",
                elapsed_ms=elapsed,
                mode=self.mode,
                adapter=self.name,
                exit_fingerprint=fingerprint,
                error=str(exc),
            )

    def _exit_fingerprint(self, url: str) -> str:
        raw = f"{self.socks_host}:{self.socks_port}:{url}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
