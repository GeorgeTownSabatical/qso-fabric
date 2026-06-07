from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from mcp_qso_edu.protocol_server import QSOEduMCPProtocolServer


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qso-edu-mcp-stdio", description="Run sandbox QSO MCP server over stdio")
    parser.add_argument(
        "--enable-upstream-apps",
        action="store_true",
        help="Allow calls to upstream MCP apps configured in QSO_EDU_UPSTREAM_APPS.",
    )
    parser.add_argument(
        "--upstream-apps",
        default=None,
        help="JSON mapping of app name to command list, equivalent to QSO_EDU_UPSTREAM_APPS.",
    )
    parser.add_argument(
        "--state-root",
        default=os.getenv("QSO_EDU_STATE_ROOT", ".codex/state/mcp_qso_edu/sandboxes"),
        help="Filesystem path for persisted sandbox operation logs.",
    )
    return parser


def dispatch_jsonrpc(server: QSOEduMCPProtocolServer, request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("id")
    try:
        result = server.handle_request(request)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": str(exc),
            },
        }


def run_stdio(args: argparse.Namespace) -> int:
    if args.upstream_apps:
        os.environ["QSO_EDU_UPSTREAM_APPS"] = args.upstream_apps

    server = QSOEduMCPProtocolServer(
        enable_upstream_apps=bool(args.enable_upstream_apps),
        state_root=args.state_root,
    )
    try:
        for line in sys.stdin:
            raw = line.strip()
            if not raw:
                continue
            try:
                request = json.loads(raw)
            except json.JSONDecodeError as exc:
                response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"parse error: {exc.msg}"},
                }
            else:
                if not isinstance(request, dict):
                    response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32600, "message": "request must be an object"},
                    }
                else:
                    response = dispatch_jsonrpc(server, request)

            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()

            method = str(request.get("method", "")).strip() if isinstance(request, dict) else ""
            if method in {"shutdown", "exit"}:
                break
    finally:
        server.close()
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(run_stdio(args))


if __name__ == "__main__":
    main()
