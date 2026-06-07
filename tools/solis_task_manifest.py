from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Mapping

DEFAULT_MANIFEST_PATH = Path("solis/reports/manifests/solis_master_task_manifest.json")
ALLOWED_STATUS = {"planned", "in_progress", "done", "blocked", "canceled"}
REQUIRED_TASK_KEYS = {
    "id",
    "phase_id",
    "title",
    "status",
    "priority",
    "owner",
    "depends_on",
    "file_targets",
    "test_targets",
    "acceptance_criteria",
}


def load_manifest(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("manifest must deserialize to a JSON object")
    return loaded


def validate_manifest(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(manifest.get("schema_version", "")) != "1.0":
        errors.append("schema_version must be '1.0'")

    phases = manifest.get("phases")
    tasks = manifest.get("tasks")
    if not isinstance(phases, list):
        errors.append("phases must be a list")
        phases = []
    if not isinstance(tasks, list):
        errors.append("tasks must be a list")
        tasks = []

    phase_ids: set[str] = set()
    for idx, phase in enumerate(phases):
        if not isinstance(phase, Mapping):
            errors.append(f"phase[{idx}] must be an object")
            continue
        phase_id = str(phase.get("id", ""))
        if not phase_id:
            errors.append(f"phase[{idx}] missing id")
            continue
        if phase_id in phase_ids:
            errors.append(f"duplicate phase id: {phase_id}")
        phase_ids.add(phase_id)

    task_ids: set[str] = set()
    depends_index: dict[str, list[str]] = {}
    for idx, task in enumerate(tasks):
        if not isinstance(task, Mapping):
            errors.append(f"task[{idx}] must be an object")
            continue

        task_key_set = set(task.keys())
        missing_keys = sorted(REQUIRED_TASK_KEYS - task_key_set)
        if missing_keys:
            errors.append(f"task[{idx}] missing keys: {','.join(missing_keys)}")
            continue

        task_id = str(task.get("id", ""))
        if not task_id:
            errors.append(f"task[{idx}] id must be non-empty")
            continue
        if task_id in task_ids:
            errors.append(f"duplicate task id: {task_id}")
            continue
        task_ids.add(task_id)

        phase_id = str(task.get("phase_id", ""))
        if phase_id not in phase_ids:
            errors.append(f"task {task_id} references unknown phase_id {phase_id}")

        status = str(task.get("status", ""))
        if status not in ALLOWED_STATUS:
            errors.append(f"task {task_id} has invalid status {status}")

        priority = task.get("priority")
        if not isinstance(priority, int):
            errors.append(f"task {task_id} priority must be int")

        depends_on = task.get("depends_on")
        if not isinstance(depends_on, list):
            errors.append(f"task {task_id} depends_on must be list")
            continue
        depends_index[task_id] = [str(dep) for dep in depends_on]
        if task_id in depends_index[task_id]:
            errors.append(f"task {task_id} cannot depend on itself")

    for task_id, deps in depends_index.items():
        for dep in deps:
            if dep not in task_ids:
                errors.append(f"task {task_id} depends on unknown task {dep}")

    if not errors:
        cycle_error = _detect_cycle(depends_index)
        if cycle_error:
            errors.append(cycle_error)

    return errors


def topological_order(manifest: Mapping[str, Any]) -> list[str]:
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list")

    graph: dict[str, list[str]] = defaultdict(list)
    indegree: dict[str, int] = {}
    for task in tasks:
        if not isinstance(task, Mapping):
            continue
        task_id = str(task["id"])
        indegree.setdefault(task_id, 0)

    for task in tasks:
        if not isinstance(task, Mapping):
            continue
        task_id = str(task["id"])
        deps = [str(dep) for dep in task.get("depends_on", [])]
        for dep in deps:
            graph[dep].append(task_id)
            indegree[task_id] = indegree.get(task_id, 0) + 1

    queue: deque[str] = deque(sorted(task_id for task_id, deg in indegree.items() if deg == 0))
    ordered: list[str] = []
    while queue:
        node = queue.popleft()
        ordered.append(node)
        for nxt in sorted(graph.get(node, [])):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(ordered) != len(indegree):
        raise ValueError("dependency cycle detected; cannot produce topological order")
    return ordered


def ready_tasks(manifest: Mapping[str, Any], *, phase: str | None = None) -> list[dict[str, Any]]:
    tasks_raw = manifest.get("tasks")
    phases_raw = manifest.get("phases")
    if not isinstance(tasks_raw, list):
        raise ValueError("tasks must be a list")
    if not isinstance(phases_raw, list):
        raise ValueError("phases must be a list")

    phase_order: dict[str, int] = {}
    for phase_obj in phases_raw:
        if isinstance(phase_obj, Mapping):
            phase_order[str(phase_obj.get("id", ""))] = int(phase_obj.get("order", 9999))

    tasks: list[dict[str, Any]] = [dict(task) for task in tasks_raw if isinstance(task, Mapping)]
    status_by_id = {str(task["id"]): str(task["status"]) for task in tasks}
    by_id = {str(task["id"]): task for task in tasks}

    ready: list[dict[str, Any]] = []
    for task in tasks:
        task_id = str(task["id"])
        status = str(task["status"])
        if status not in {"planned", "in_progress"}:
            continue
        phase_id = str(task["phase_id"])
        if phase is not None and phase_id != phase:
            continue
        deps = [str(dep) for dep in task.get("depends_on", [])]
        if any(status_by_id.get(dep) != "done" for dep in deps):
            continue
        ready.append(by_id[task_id])

    ready.sort(
        key=lambda task: (
            phase_order.get(str(task["phase_id"]), 9999),
            -int(task.get("priority", 0)),
            str(task["id"]),
        )
    )
    return ready


def _detect_cycle(depends_index: Mapping[str, list[str]]) -> str | None:
    visited: set[str] = set()
    active: set[str] = set()

    def dfs(node: str) -> str | None:
        if node in active:
            return node
        if node in visited:
            return None
        visited.add(node)
        active.add(node)
        for dep in depends_index.get(node, []):
            cycle_at = dfs(dep)
            if cycle_at is not None:
                return cycle_at
        active.remove(node)
        return None

    for node in depends_index:
        cycle_at = dfs(node)
        if cycle_at is not None:
            return f"dependency cycle detected at task {cycle_at}"
    return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and query Solis task DAG manifests.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help=f"Manifest path (default: {DEFAULT_MANIFEST_PATH})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="Validate manifest schema and dependency graph")
    sub.add_parser("topo", help="Print topological task order")

    next_cmd = sub.add_parser("next", help="List tasks ready to execute")
    next_cmd.add_argument("--phase", default=None, help="Optional phase filter (e.g., P02)")
    next_cmd.add_argument("--limit", type=int, default=10, help="Max tasks to print")
    next_cmd.add_argument("--json", action="store_true", help="Print JSON output")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)

    if args.command == "validate":
        errors = validate_manifest(manifest)
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("OK: manifest is valid")
        return 0

    if args.command == "topo":
        errors = validate_manifest(manifest)
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        for task_id in topological_order(manifest):
            print(task_id)
        return 0

    if args.command == "next":
        errors = validate_manifest(manifest)
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        tasks = ready_tasks(manifest, phase=args.phase)
        if args.limit >= 0:
            tasks = tasks[: args.limit]
        if args.json:
            print(json.dumps(tasks, indent=2))
        else:
            for task in tasks:
                print(f"{task['id']} | phase={task['phase_id']} | priority={task['priority']} | {task['title']}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
