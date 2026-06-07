from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from qso_xr.program_management import (
    append_program_event,
    build_program_state,
    compute_state_hash,
    utc_now_iso,
    write_program_state,
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _read_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"state file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("program state must be object")
    return payload


def _write_state(path: Path, state: Dict[str, Any]) -> None:
    write_program_state(path, state)


def _task_index(tasks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(task["task_id"]): task for task in tasks}


def _next_actionable_tasks(state: Dict[str, Any], *, limit: int) -> List[Dict[str, Any]]:
    tasks = [dict(task) for task in state.get("tasks", []) if isinstance(task, dict)]
    by_id = _task_index(tasks)
    actionable: List[Dict[str, Any]] = []
    for task in tasks:
        if task.get("status") not in {"planned", "active"}:
            continue
        deps = list(task.get("dependencies", []))
        blocked = False
        for dep in deps:
            dep_task = by_id.get(str(dep))
            if not dep_task or dep_task.get("status") != "done":
                blocked = True
                break
        if not blocked:
            actionable.append(task)
    actionable.sort(key=lambda row: (int(row.get("priority", 99)), str(row.get("planned_start", "")), str(row.get("task_id", ""))))
    return actionable[: max(1, int(limit))]


def cmd_init(state_path: Path, events_path: Path, *, force: bool) -> int:
    if state_path.exists() and not force:
        raise FileExistsError(f"state file already exists: {state_path} (use --force)")
    state = build_program_state()
    _write_state(state_path, state)
    append_program_event(
        events_path,
        event_type="program_initialized",
        summary="Initialized XR framework program schedule and backlog",
        payload={"state_path": str(state_path), "task_count": len(state.get("tasks", []))},
    )
    print(_canonical({"status": "ok", "state_path": str(state_path), "events_path": str(events_path)}))
    return 0


def cmd_status(state_path: Path, *, as_json: bool) -> int:
    state = _read_state(state_path)
    tasks = [dict(row) for row in state.get("tasks", []) if isinstance(row, dict)]
    milestones = [dict(row) for row in state.get("milestones", []) if isinstance(row, dict)]
    done = sum(1 for row in tasks if row.get("status") == "done")
    active = sum(1 for row in tasks if row.get("status") == "active")
    planned = sum(1 for row in tasks if row.get("status") == "planned")
    payload = {
        "program": state.get("program", {}),
        "counts": {"tasks_total": len(tasks), "done": done, "active": active, "planned": planned},
        "milestones": milestones,
    }
    if as_json:
        print(_canonical(payload))
    else:
        print(f"tasks_total={len(tasks)} done={done} active={active} planned={planned}")
        for row in milestones:
            print(f"{row.get('milestone_id')} {row.get('title')} [{row.get('window_start')}..{row.get('window_end')}] status={row.get('status')}")
    return 0


def cmd_next(state_path: Path, *, limit: int, as_json: bool) -> int:
    state = _read_state(state_path)
    rows = _next_actionable_tasks(state, limit=limit)
    if as_json:
        print(_canonical({"tasks": rows}))
    else:
        for task in rows:
            print(f"{task.get('task_id')} p{task.get('priority')} {task.get('title')} [{task.get('planned_start')}..{task.get('planned_end')}]")
    return 0


def cmd_set_task_status(
    state_path: Path,
    events_path: Path,
    *,
    task_id: str,
    status: str,
    note: str,
) -> int:
    allowed = {"planned", "active", "done", "blocked", "canceled"}
    if status not in allowed:
        raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}")
    state = _read_state(state_path)
    tasks = [dict(row) for row in state.get("tasks", []) if isinstance(row, dict)]
    index = _task_index(tasks)
    if task_id not in index:
        raise KeyError(f"task not found: {task_id}")
    task = index[task_id]
    task["status"] = status
    if note:
        task["note"] = note
    state["tasks"] = tasks
    state["updated_at"] = utc_now_iso()
    state["state_hash"] = compute_state_hash(state)
    _write_state(state_path, state)
    append_program_event(
        events_path,
        event_type="task_status_updated",
        summary=f"Task {task_id} -> {status}",
        payload={"task_id": task_id, "status": status, "note": note},
    )
    print(_canonical({"status": "ok", "task_id": task_id, "new_status": status}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QSO XR program scheduler and milestone manager")
    parser.add_argument("--state-path", default=".codex/state/xr_program_state.json", help="Program state path")
    parser.add_argument("--events-path", default=".codex/state/xr_program_events.jsonl", help="Program event log path")

    sub = parser.add_subparsers(dest="command", required=True)
    init_cmd = sub.add_parser("init", help="Initialize program state + events log")
    init_cmd.add_argument("--force", action="store_true", help="Overwrite existing state file")

    status_cmd = sub.add_parser("status", help="Show milestone and task counts")
    status_cmd.add_argument("--json", action="store_true", help="Emit JSON")

    next_cmd = sub.add_parser("next", help="List next actionable tasks")
    next_cmd.add_argument("--limit", type=int, default=5, help="Max tasks to list")
    next_cmd.add_argument("--json", action="store_true", help="Emit JSON")

    set_cmd = sub.add_parser("set-status", help="Set task status")
    set_cmd.add_argument("--task-id", required=True, help="Task id")
    set_cmd.add_argument("--status", required=True, help="planned|active|done|blocked|canceled")
    set_cmd.add_argument("--note", default="", help="Optional status note")
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    state_path = Path(args.state_path)
    events_path = Path(args.events_path)

    if args.command == "init":
        return cmd_init(state_path, events_path, force=bool(args.force))
    if args.command == "status":
        return cmd_status(state_path, as_json=bool(args.json))
    if args.command == "next":
        return cmd_next(state_path, limit=int(args.limit), as_json=bool(args.json))
    if args.command == "set-status":
        return cmd_set_task_status(
            state_path,
            events_path,
            task_id=str(args.task_id),
            status=str(args.status),
            note=str(args.note),
        )
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
