"""
codex_orchestrator.py

A lightweight task orchestrator for the CSTE + Multilattice development program.

Features:
- Loads task registry from YAML
- Validates task uniqueness and dependency references
- Computes ready tasks
- Assigns tasks to agents
- Updates status safely
- Writes structured JSONL audit logs
- Prints execution summaries

This is intentionally conservative and transparent. It does not execute arbitrary code.
It is designed to manage task flow and can later be extended with actual agent backends.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import json

try:
    import yaml
except ImportError as exc:
    raise RuntimeError(
        "PyYAML is required. Install it with: pip install pyyaml"
    ) from exc


VALID_STATUSES = {
    "pending",
    "ready",
    "in_progress",
    "blocked",
    "review",
    "done",
    "failed",
    "archived",
}


@dataclass
class Task:
    id: str
    title: str
    phase: str
    module: str
    description: str
    assignee: str
    priority: str
    status: str = "pending"
    dependencies: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    validation: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Task":
        missing = [k for k in ["id", "title", "phase", "module", "description", "assignee", "priority"] if k not in payload]
        if missing:
            raise ValueError(f"Task is missing required fields: {missing}")
        status = payload.get("status", "pending")
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}' for task {payload.get('id')}")
        return cls(
            id=payload["id"],
            title=payload["title"],
            phase=payload["phase"],
            module=payload["module"],
            description=payload["description"],
            assignee=payload["assignee"],
            priority=payload["priority"],
            status=status,
            dependencies=list(payload.get("dependencies", [])),
            outputs=list(payload.get("outputs", [])),
            validation=list(payload.get("validation", [])),
        )


class TaskRegistry:
    def __init__(self, tasks: List[Task], metadata: Optional[Dict[str, Any]] = None):
        self.tasks: Dict[str, Task] = {task.id: task for task in tasks}
        self.metadata = metadata or {}

    @classmethod
    def load_from_yaml(cls, path: Path) -> "TaskRegistry":
        if not path.exists():
            raise FileNotFoundError(f"Task file not found: {path}")

        with path.open("r", encoding="utf-8") as fh:
            payload = yaml.safe_load(fh)

        task_dicts = payload.get("tasks", [])
        tasks = [Task.from_dict(item) for item in task_dicts]
        registry = cls(tasks=tasks, metadata=payload.get("metadata", {}))
        registry.validate()
        registry.refresh_ready_states()
        return registry

    def validate(self) -> None:
        if len(self.tasks) == 0:
            raise ValueError("Registry contains no tasks")

        seen: Set[str] = set()
        for task in self.tasks.values():
            if task.id in seen:
                raise ValueError(f"Duplicate task id: {task.id}")
            seen.add(task.id)

            unknown = [dep for dep in task.dependencies if dep not in self.tasks]
            if unknown:
                raise ValueError(f"Task {task.id} references unknown dependencies: {unknown}")

            if task.id in task.dependencies:
                raise ValueError(f"Task {task.id} depends on itself")

        self._validate_cycles()

    def _validate_cycles(self) -> None:
        visited: Set[str] = set()
        active: Set[str] = set()

        def dfs(task_id: str) -> None:
            if task_id in active:
                raise ValueError(f"Dependency cycle detected at task {task_id}")
            if task_id in visited:
                return
            visited.add(task_id)
            active.add(task_id)
            for dep in self.tasks[task_id].dependencies:
                dfs(dep)
            active.remove(task_id)

        for task_id in self.tasks:
            dfs(task_id)

    def refresh_ready_states(self) -> None:
        for task in self.tasks.values():
            if task.status in {"done", "archived", "failed", "in_progress", "review"}:
                continue
            if all(self.tasks[dep].status == "done" for dep in task.dependencies):
                task.status = "ready"
            elif task.dependencies:
                task.status = "blocked"
            else:
                task.status = "ready"

    def get_task(self, task_id: str) -> Task:
        if task_id not in self.tasks:
            raise KeyError(f"Unknown task id: {task_id}")
        return self.tasks[task_id]

    def ready_tasks(self) -> List[Task]:
        self.refresh_ready_states()
        return sorted(
            [task for task in self.tasks.values() if task.status == "ready"],
            key=lambda t: (self._priority_rank(t.priority), t.id),
        )

    def tasks_by_status(self, status: str) -> List[Task]:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status {status}")
        return sorted([task for task in self.tasks.values() if task.status == status], key=lambda t: t.id)

    def assign_task(self, task_id: str, assignee: Optional[str] = None) -> Task:
        task = self.get_task(task_id)
        self.refresh_ready_states()
        if task.status != "ready":
            raise ValueError(f"Task {task_id} is not ready; current status is {task.status}")
        if assignee:
            task.assignee = assignee
        task.status = "in_progress"
        return task

    def update_status(self, task_id: str, new_status: str) -> Task:
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")

        task = self.get_task(task_id)

        if new_status == "done":
            incomplete = [dep for dep in task.dependencies if self.tasks[dep].status != "done"]
            if incomplete:
                raise ValueError(f"Cannot mark {task_id} done; unresolved dependencies: {incomplete}")

        task.status = new_status
        self.refresh_ready_states()
        return task

    def summary(self) -> Dict[str, int]:
        counts = {status: 0 for status in VALID_STATUSES}
        for task in self.tasks.values():
            counts[task.status] += 1
        return counts

    def next_tasks_for_agent(self, agent_name: str, limit: int = 5) -> List[Task]:
        ready = self.ready_tasks()
        filtered = [task for task in ready if task.assignee == agent_name]
        return filtered[:limit]

    @staticmethod
    def _priority_rank(priority: str) -> int:
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return order.get(priority.lower(), 9)


class AuditLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: Dict[str, Any]) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **event,
        }
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


class CodexOrchestrator:
    def __init__(self, registry: TaskRegistry, logger: Optional[AuditLogger] = None):
        self.registry = registry
        self.logger = logger

    def log(self, action: str, task: Optional[Task] = None, details: Optional[Dict[str, Any]] = None) -> None:
        if not self.logger:
            return
        event: Dict[str, Any] = {"action": action}
        if task:
            event["task_id"] = task.id
            event["task_title"] = task.title
            event["status"] = task.status
            event["assignee"] = task.assignee
        if details:
            event["details"] = details
        self.logger.write(event)

    def show_summary(self) -> None:
        summary = self.registry.summary()
        print("Task summary:")
        for status in sorted(summary):
            print(f"  {status:>11}: {summary[status]}")

    def show_ready(self, limit: int = 20) -> None:
        ready = self.registry.ready_tasks()[:limit]
        if not ready:
            print("No ready tasks.")
            return
        print("Ready tasks:")
        for task in ready:
            print(f"- {task.id} | {task.assignee} | {task.priority} | {task.title}")

    def assign(self, task_id: str, assignee: Optional[str] = None) -> Task:
        task = self.registry.assign_task(task_id, assignee=assignee)
        self.log("assign", task)
        return task

    def mark(self, task_id: str, status: str) -> Task:
        task = self.registry.update_status(task_id, status)
        self.log("status_update", task, details={"new_status": status})
        return task

    def recommend_batch(self, limit: int = 10) -> List[Task]:
        ready = self.registry.ready_tasks()
        batch = ready[:limit]
        self.log("recommend_batch", details={"count": len(batch)})
        return batch

    def print_batch(self, limit: int = 10) -> None:
        batch = self.recommend_batch(limit=limit)
        if not batch:
            print("No recommended tasks.")
            return
        print("Recommended batch:")
        for task in batch:
            print(f"- {task.id} [{task.priority}] -> {task.assignee} :: {task.title}")

    def export_status_json(self, path: Path) -> None:
        payload = {
            "summary": self.registry.summary(),
            "tasks": [asdict(task) for task in self.registry.tasks.values()],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.log("export_status", details={"path": str(path)})


def build_orchestrator(task_file: Path, log_file: Optional[Path] = None) -> CodexOrchestrator:
    registry = TaskRegistry.load_from_yaml(task_file)
    logger = AuditLogger(log_file) if log_file else None
    return CodexOrchestrator(registry=registry, logger=logger)


def demo() -> None:
    task_file = Path("tasks.yaml")
    log_file = Path("logs/orchestrator.jsonl")

    orchestrator = build_orchestrator(task_file=task_file, log_file=log_file)

    orchestrator.show_summary()
    print()
    orchestrator.show_ready(limit=15)
    print()

    batch = orchestrator.recommend_batch(limit=5)
    if batch:
        chosen = batch[0]
        print(f"Assigning {chosen.id} to {chosen.assignee}")
        orchestrator.assign(chosen.id)
        orchestrator.mark(chosen.id, "review")
        orchestrator.mark(chosen.id, "done")

    print()
    orchestrator.show_summary()
    orchestrator.export_status_json(Path("logs/task_status.json"))


if __name__ == "__main__":
    demo()
