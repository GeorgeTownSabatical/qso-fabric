"""Autonomous investigation cycle runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.reasoning_loop import run_cycle


def main() -> int:
    parser = argparse.ArgumentParser(description="Run autonomous investigation cycle")
    parser.add_argument("--graph-json", type=Path, required=True)
    parser.add_argument("--reasoning-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "outputs")
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--max-cycles", type=int, default=1)
    args = parser.parse_args()

    cycle_reports = []
    for i in range(args.max_cycles):
        report = run_cycle(args.graph_json, args.reasoning_dir, args.output_dir)
        cycle_reports.append(report)
        print(json.dumps({"cycle": i + 1, **report}, indent=2))
        if i < args.max_cycles - 1:
            time.sleep(args.interval_seconds)

    summary = {
        "cycles": len(cycle_reports),
        "total_generated": sum(r["generated_hypotheses"] for r in cycle_reports),
        "total_confirmed": sum(r["confirmed"] for r in cycle_reports),
        "total_rejected": sum(r["rejected"] for r in cycle_reports),
    }
    (args.output_dir / "autonomous_cycle_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
