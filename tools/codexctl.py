from __future__ import annotations

import argparse
import sys

from tools.codexctl_transport import run as run_transport


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codexctl", description="Codex control CLI")
    sub = parser.add_subparsers(dest="domain", required=True)

    transport = sub.add_parser("transport", help="Transport governance controls")
    transport.add_argument("transport_args", nargs=argparse.REMAINDER)
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.domain == "transport":
        if not args.transport_args:
            # Delegate to transport parser for help.
            return run_transport(["status"])
        return run_transport(list(args.transport_args))

    parser.print_help()
    return 2


def main() -> None:
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
