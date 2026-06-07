from __future__ import annotations

import argparse
import json
import sys

from api.mcp_tools.qso_tools import QSOMCPTools


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codexctl transport", description="QSO transport governance controls")
    sub = parser.add_subparsers(dest="command", required=True)

    set_cmd = sub.add_parser("set", help="Set active transport mode")
    set_cmd.add_argument("mode", choices=["direct", "vpn", "tor"])
    set_cmd.add_argument("--actor", default="codexctl")
    set_cmd.add_argument("--policy-version", default="v1")
    set_cmd.add_argument("--node-id", default="local")

    sub.add_parser("status", help="Show transport status")
    sub.add_parser("health", help="Show transport health snapshots")
    sub.add_parser("policy", help="Show transport policy map")

    return parser


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    tools = QSOMCPTools()

    if args.command == "set":
        payload = tools.qso_transport_set(
            mode=args.mode,
            actor=args.actor,
            policy_version=args.policy_version,
            node_id=args.node_id,
        )
    elif args.command == "status":
        payload = tools.qso_transport_status()
    elif args.command == "health":
        payload = tools.qso_transport_health()
    elif args.command == "policy":
        payload = tools.qso_transport_policy()
    else:
        parser.print_help()
        return 2

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
