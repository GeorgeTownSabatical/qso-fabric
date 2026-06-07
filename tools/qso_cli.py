from __future__ import annotations

import argparse
import json

from mcp_server.server_core import MCPServer


def main() -> None:
    parser = argparse.ArgumentParser(description="QSO CLI")
    parser.add_argument("action", choices=["create", "read", "patch"])
    parser.add_argument("uri")
    parser.add_argument("--payload", default="{}")
    args = parser.parse_args()

    server = MCPServer()
    server.start()
    tools = server.tools

    payload = json.loads(args.payload)

    if args.action == "create":
        print(json.dumps(tools.qso_create(args.uri, payload), indent=2))
    elif args.action == "read":
        print(json.dumps(tools.qso_read(args.uri), indent=2))
    else:
        print(json.dumps(tools.qso_patch(args.uri, payload), indent=2))


if __name__ == "__main__":
    main()
