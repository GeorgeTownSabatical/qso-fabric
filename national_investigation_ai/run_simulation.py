"""Run control-node + worker simulation locally."""

from __future__ import annotations

import json
from pathlib import Path

from control.orchestrator import Orchestrator
from control.task_dispatcher import TaskDispatcher
from worker.worker_node import run_worker


BASE = Path(__file__).resolve().parent


def main() -> int:
    orchestrator = Orchestrator(BASE)
    tasks = orchestrator.dispatch_standard_cycle()

    run_worker("worker-sim-1", max_tasks=6, poll_seconds=0)

    dispatcher = TaskDispatcher(BASE / "data" / "queue" / "tasks.json", BASE / "data" / "results" / "results.json")
    queue = dispatcher.queue_state()
    results = dispatcher.results()

    summary = {
        "tasks_dispatched": len(tasks),
        "queue_done": len([t for t in queue if t.get("status") == "done"]),
        "queue_failed": len([t for t in queue if t.get("status") == "failed"]),
        "results": len(results),
    }
    (BASE / "data" / "results" / "simulation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
