"""Standalone hypothesis loop."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.hypothesis_agent import HypothesisAgent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=2700)
    parser.add_argument("--max-runs", type=int, default=1)
    args = parser.parse_args()

    agent = HypothesisAgent()
    for i in range(args.max_runs):
        result = agent.run()
        print(json.dumps({"run": i + 1, "returncode": result["returncode"]}, indent=2))
        if i < args.max_runs - 1:
            time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
