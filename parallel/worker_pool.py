from __future__ import annotations

from dataclasses import dataclass

from .task_queue import TaskQueue, Task


@dataclass
class WorkerPool:
    size: int

    def run(self, queue: TaskQueue) -> list[Task]:
        completed: list[Task] = []
        while True:
            task = queue.pop()
            if task is None:
                break
            completed.append(task)
        return completed
