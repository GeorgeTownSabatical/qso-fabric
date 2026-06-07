"""Neighbor expansion pipeline."""

from __future__ import annotations

import argparse
from collections import deque

from agents.gis_agent import GISAgent
from pipeline.run_pipeline import run_pipeline


def expand_neighbors(apn: str, depth: int = 1) -> list[str]:
    gis = GISAgent()
    visited = set([apn])
    queue = deque([(apn, 0)])
    executed = []

    while queue:
        current, level = queue.popleft()
        result = run_pipeline(current)
        executed.append(result["apn"])
        if level >= depth:
            continue
        for neighbor in gis.get_neighbors(current):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append((neighbor, level + 1))

    return executed


def main() -> int:
    parser = argparse.ArgumentParser(description="Run APN pipeline and expand to neighbors")
    parser.add_argument("apn")
    parser.add_argument("--depth", type=int, default=1)
    args = parser.parse_args()

    executed = expand_neighbors(args.apn, depth=args.depth)
    print({"count": len(executed), "apns": executed})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
