"""Control-node orchestrator."""

from __future__ import annotations

from pathlib import Path

from control.task_dispatcher import TaskDispatcher


class Orchestrator:
    def __init__(self, base: Path):
        self.base = base
        self.dispatcher = TaskDispatcher(base / "data" / "queue" / "tasks.json", base / "data" / "results" / "results.json")

    def dispatch_standard_cycle(self) -> list[dict]:
        tasks = []
        tasks.append(self.dispatcher.publish("ingestion", {}))
        tasks.append(self.dispatcher.publish("reasoning", {}))
        tasks.append(self.dispatcher.publish("hypothesis", {}))
        return tasks
