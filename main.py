from __future__ import annotations

import argparse
import os
from pathlib import Path

from api.rest import QSOIdentityRESTAPI, create_http_server
from core.naming.snapshot_terms import resolve_snapshot_artifact_path
from mcp_server.server_core import MCPServer


def _seed_demo(server: MCPServer) -> None:
    server.tools.qso_create("qso://ai.model.core", {"type": "model"})
    server.tools.qso_create("qso://vr.world.city_01", {"type": "scene"})
    server.tools.qso_entangle("qso://ai.model.core", "qso://vr.world.city_01", "dependent")
    server.tools.qso_patch("qso://ai.model.core", {"weights": {"v": 1}}, actor="bootstrap")


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def main() -> None:
    parser = argparse.ArgumentParser(description="QSO Fabric runtime")
    parser.add_argument(
        "--serve-http",
        action="store_true",
        default=_env_flag("QSO_SERVE_HTTP", False),
        help="Run HTTP API server.",
    )
    parser.add_argument("--host", default=os.getenv("QSO_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=_env_int("QSO_PORT", 8000))
    parser.add_argument(
        "--seed-demo",
        action="store_true",
        default=_env_flag("QSO_SEED_DEMO", False),
        help="Create demo QSOs on boot.",
    )
    parser.add_argument(
        "--max-request-bytes",
        type=int,
        default=_env_int("QSO_HTTP_MAX_REQUEST_BYTES", 1_048_576),
        help="Maximum accepted HTTP request body size in bytes.",
    )
    args = parser.parse_args()

    server = MCPServer()
    server.start()

    if args.seed_demo:
        _seed_demo(server)

    if args.serve_http:
        http_api = QSOIdentityRESTAPI(tools=server.tools, max_request_bytes=max(4096, int(args.max_request_bytes)))
        http_server = create_http_server(host=args.host, port=args.port, api=http_api)
        try:
            http_server.serve_forever()
        finally:
            http_server.server_close()
            server.stop()
        return

    blob = server.tools.qso_export_snapshot("qso://ai.model.core") if args.seed_demo else b""
    if blob:
        artifact_path = resolve_snapshot_artifact_path("ai_model_snapshot.qff")
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        with artifact_path.open("wb") as f:
            f.write(blob)
    server.stop()


if __name__ == "__main__":
    main()
