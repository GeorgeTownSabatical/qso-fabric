from __future__ import annotations

import argparse

from mapl.executor import run


def main() -> int:
    parser = argparse.ArgumentParser(prog="mapl")
    parser.add_argument("command", help="MAPL command string")
    args = parser.parse_args()
    result = run(args.command)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
