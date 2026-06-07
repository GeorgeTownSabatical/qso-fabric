from __future__ import annotations

import argparse
import json
import os
import ssl
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from mcp_qso_edu.conversation_bridge import ConversationBridge


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qso-plus-bridge-http", description="Run local ChatGPT-bridge HTTP relay")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--path", default=".codex/state/plus_bridge.jsonl")
    parser.add_argument("--tls-cert", default=None, help="PEM certificate path (enables HTTPS when set with --tls-key)")
    parser.add_argument("--tls-key", default=None, help="PEM private key path (enables HTTPS when set with --tls-cert)")
    parser.add_argument(
        "--auth-token",
        default=os.getenv("QSO_BRIDGE_AUTH_TOKEN"),
        help="Static bearer token for API access (recommended for SOC2-style controls).",
    )
    parser.add_argument(
        "--allowed-origin",
        default=os.getenv("QSO_BRIDGE_ALLOWED_ORIGIN"),
        help="Exact allowed CORS origin, e.g. https://chat.example.com. Omit to disable CORS headers.",
    )
    parser.add_argument("--max-body-bytes", type=int, default=64 * 1024)
    parser.add_argument("--max-requests-per-minute", type=int, default=240)
    parser.add_argument("--audit-log", default=".codex/state/plus_bridge_access.jsonl")
    return parser


def _build_tls_context(tls_cert: str | None, tls_key: str | None) -> ssl.SSLContext | None:
    cert = (tls_cert or "").strip()
    key = (tls_key or "").strip()
    if not cert and not key:
        return None
    if not cert or not key:
        raise ValueError("both --tls-cert and --tls-key are required to enable HTTPS")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=cert, keyfile=key)
    return context


@dataclass(slots=True)
class BridgeSecurity:
    auth_token: str | None
    allowed_origin: str | None
    max_body_bytes: int
    max_requests_per_minute: int
    audit_log_path: Path


class AccessAuditor:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def log(
        self,
        *,
        request_id: str,
        client_ip: str,
        method: str,
        path: str,
        status: int,
        detail: str = "",
    ) -> None:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "client_ip": client_ip,
            "method": method,
            "path": path,
            "status": status,
            "detail": detail,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


class PerIPRateLimiter:
    def __init__(self, max_requests_per_minute: int) -> None:
        self.max_requests_per_minute = max(1, int(max_requests_per_minute))
        self._by_ip: dict[str, deque[datetime]] = defaultdict(deque)

    def allow(self, ip: str) -> bool:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=1)
        queue = self._by_ip[str(ip)]
        while queue and queue[0] < cutoff:
            queue.popleft()
        if len(queue) >= self.max_requests_per_minute:
            return False
        queue.append(now)
        return True


def run_server(
    host: str,
    port: int,
    path: str,
    *,
    tls_cert: str | None = None,
    tls_key: str | None = None,
    auth_token: str | None = None,
    allowed_origin: str | None = None,
    max_body_bytes: int = 64 * 1024,
    max_requests_per_minute: int = 240,
    audit_log: str | Path = ".codex/state/plus_bridge_access.jsonl",
) -> int:
    bridge = ConversationBridge(path)
    security = BridgeSecurity(
        auth_token=(auth_token or "").strip() or None,
        allowed_origin=(allowed_origin or "").strip() or None,
        max_body_bytes=max(1024, int(max_body_bytes)),
        max_requests_per_minute=max(1, int(max_requests_per_minute)),
        audit_log_path=Path(audit_log),
    )
    auditor = AccessAuditor(security.audit_log_path)
    limiter = PerIPRateLimiter(security.max_requests_per_minute)

    class Handler(BaseHTTPRequestHandler):
        def do_OPTIONS(self) -> None:
            request_id = self._request_id()
            if not self._authorize():
                self._send_json(401, {"error": "unauthorized"}, request_id=request_id)
                self._log(request_id, 401, "unauthorized")
                return
            self._send_json(200, {"ok": True}, request_id=request_id)
            self._log(request_id, 200)

        def do_GET(self) -> None:
            request_id = self._request_id()
            if not self._preflight_ok(request_id):
                return
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self._send_json(200, {"ok": True, "service": "qso-plus-bridge-http"}, request_id=request_id)
                self._log(request_id, 200)
                return
            if parsed.path != "/bridge/read":
                self._send_json(404, {"error": "not found"}, request_id=request_id)
                self._log(request_id, 404)
                return
            query = parse_qs(parsed.query)
            after_seq = int(query.get("after_seq", ["0"])[0])
            limit = int(query.get("limit", ["200"])[0])
            payload = bridge.read(after_seq=after_seq, limit=limit)
            self._send_json(200, payload, request_id=request_id)
            self._log(request_id, 200)

        def do_POST(self) -> None:
            request_id = self._request_id()
            if not self._preflight_ok(request_id):
                return
            parsed = urlparse(self.path)
            if parsed.path != "/bridge/append":
                self._send_json(404, {"error": "not found"}, request_id=request_id)
                self._log(request_id, 404)
                return

            body = self._read_json()
            if not isinstance(body, dict):
                self._send_json(400, {"error": "invalid json body"}, request_id=request_id)
                self._log(request_id, 400, "invalid_json")
                return

            try:
                payload = bridge.append(
                    source=str(body.get("source", "")),
                    content=str(body.get("content", "")),
                    session_id=str(body.get("session_id", "shared")),
                    metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else {},
                )
            except Exception as exc:
                self._send_json(400, {"error": str(exc)}, request_id=request_id)
                self._log(request_id, 400, "append_failed")
                return

            self._send_json(200, payload, request_id=request_id)
            self._log(request_id, 200)

        def log_message(self, fmt: str, *args: Any) -> None:
            return None

        def _preflight_ok(self, request_id: str) -> bool:
            if not self._authorize():
                self._send_json(401, {"error": "unauthorized"}, request_id=request_id)
                self._log(request_id, 401, "unauthorized")
                return False
            if not limiter.allow(self._client_ip()):
                self._send_json(429, {"error": "rate_limited"}, request_id=request_id)
                self._log(request_id, 429, "rate_limited")
                return False
            return True

        def _authorize(self) -> bool:
            token = security.auth_token
            if token is None:
                return True
            authorization = str(self.headers.get("authorization", "")).strip()
            if authorization.lower().startswith("bearer "):
                supplied = authorization[7:].strip()
                return supplied == token
            supplied = str(self.headers.get("x-bridge-token", "")).strip()
            return supplied == token

        def _request_id(self) -> str:
            supplied = str(self.headers.get("x-request-id", "")).strip()
            return supplied or uuid.uuid4().hex

        def _client_ip(self) -> str:
            return str(self.client_address[0]) if self.client_address else "unknown"

        def _log(self, request_id: str, status: int, detail: str = "") -> None:
            auditor.log(
                request_id=request_id,
                client_ip=self._client_ip(),
                method=self.command,
                path=self.path,
                status=status,
                detail=detail,
            )

        def _read_json(self) -> dict[str, Any] | list[Any] | None:
            length = int(self.headers.get("content-length", "0"))
            if length <= 0:
                return None
            if length > security.max_body_bytes:
                return None
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw)

        def _send_json(self, status: int, payload: dict[str, Any], *, request_id: str) -> None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Request-Id", request_id)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            if security.allowed_origin:
                origin = str(self.headers.get("origin", "")).strip()
                if origin == security.allowed_origin:
                    self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Headers", "content-type,authorization,x-bridge-token,x-request-id")
                self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer((host, port), Handler)
    tls_context = _build_tls_context(tls_cert, tls_key)
    if tls_context is not None:
        server.socket = tls_context.wrap_socket(server.socket, server_side=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(
        run_server(
            args.host,
            args.port,
            args.path,
            tls_cert=args.tls_cert,
            tls_key=args.tls_key,
            auth_token=args.auth_token,
            allowed_origin=args.allowed_origin,
            max_body_bytes=args.max_body_bytes,
            max_requests_per_minute=args.max_requests_per_minute,
            audit_log=args.audit_log,
        )
    )


if __name__ == "__main__":
    main()
