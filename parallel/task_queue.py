from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    name: str
    payload: dict[str, object]


class TaskQueue:
    def __init__(self) -> None:
        self._queue: deque[Task] = deque()

    def push(self, task: Task) -> None:
        self._queue.append(task)

    def pop(self) -> Task | None:
        if not self._queue:
            return None
        return self._queue.popleft()
