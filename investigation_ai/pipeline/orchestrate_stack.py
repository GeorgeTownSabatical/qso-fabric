"""Single command to run full local stack cycle."""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.orchestrator import run_stack_once


def main() -> int:
    summary = run_stack_once()
    print(json.dumps({
        "ingestion_ok": summary["ingestion_ok"],
        "reasoning_ok": summary["reasoning_ok"],
        "hypothesis_ok": summary["hypothesis_ok"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
