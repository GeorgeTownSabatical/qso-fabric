from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod

from services.transport.models import TransportMode, TransportRequest, TransportResponse


class BaseTransport(ABC):
    mode: TransportMode
    name: str

    @abstractmethod
    def send(self, request: TransportRequest) -> TransportResponse:
        raise NotImplementedError

    def _mock_response(self, request: TransportRequest, *, mode: TransportMode, adapter: str, exit_fingerprint: str = "") -> TransportResponse:
        started = time.perf_counter()
        digest = hashlib.sha256((request.method + request.url).encode("utf-8")).hexdigest()[:16]
        body = {
            "ok": True,
            "method": request.method,
            "url": request.url,
            "adapter": adapter,
            "mode": mode.value,
            "digest": digest,
            "metadata": request.metadata,
        }
        payload = json.dumps(body, sort_keys=True).encode("utf-8")
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return TransportResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            body=payload,
            elapsed_ms=elapsed_ms,
            mode=mode,
            adapter=adapter,
            exit_fingerprint=exit_fingerprint,
        )
