"""Worker loop for pulling and executing tasks."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from control.node_registry import NodeRegistry
from control.task_dispatcher import TaskDispatcher
from worker.task_executor import execute_task


BASE = Path(__file__).resolve().parents[1]


def run_worker(node_id: str, max_tasks: int = 10, poll_seconds: int = 1) -> dict:
    registry = NodeRegistry(BASE / "data" / "queue" / "nodes.json")
    dispatcher = TaskDispatcher(BASE / "data" / "queue" / "tasks.json", BASE / "data" / "results" / "results.json")

    registry.register(node_id=node_id, role="worker")

    processed = 0
    while processed < max_tasks:
        registry.heartbeat(node_id)
        task = dispatcher.fetch_next()
        if not task:
            time.sleep(poll_seconds)
            processed += 1
            continue
        ok, result = execute_task(task)
        dispatcher.complete(task["task_id"], result, ok)
        processed += 1

    return {"node_id": node_id, "processed_slots": processed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run worker node")
    parser.add_argument("--node-id", default="worker-1")
    parser.add_argument("--max-tasks", type=int, default=6)
    args = parser.parse_args()
    print(run_worker(args.node_id, max_tasks=args.max_tasks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
