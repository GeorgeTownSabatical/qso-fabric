from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from qso_xr.program_management import append_program_event, compute_state_hash, utc_now_iso, write_program_state


AUTOPILOT_SCHEMA_VERSION = "1.0"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    raw = str(ts).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def _read_program_state(path: Path) -> Dict[str, Any]:
    return _read_json(path)


def _default_autopilot_state(interval_minutes: int, timeout_minutes: int) -> Dict[str, Any]:
    now = utc_now_iso()
    return {
        "schema_version": AUTOPILOT_SCHEMA_VERSION,
        "created_at": now,
        "updated_at": now,
        "enabled": True,
        "check_interval_minutes": int(interval_minutes),
        "no_response_timeout_minutes": int(timeout_minutes),
        "last_tick_at": None,
        "last_user_ack_at": now,
        "last_action": "initialized",
    }


def _read_or_init_autopilot_state(path: Path, interval_minutes: int, timeout_minutes: int) -> Dict[str, Any]:
    if path.exists():
        payload = _read_json(path)
        payload.setdefault("schema_version", AUTOPILOT_SCHEMA_VERSION)
        payload.setdefault("enabled", True)
        payload.setdefault("check_interval_minutes", int(interval_minutes))
        payload.setdefault("no_response_timeout_minutes", int(timeout_minutes))
        payload.setdefault("last_tick_at", None)
        payload.setdefault("last_user_ack_at", None)
        payload.setdefault("last_action", "loaded")
        payload.setdefault("created_at", utc_now_iso())
        payload.setdefault("updated_at", utc_now_iso())
        return payload
    payload = _default_autopilot_state(interval_minutes, timeout_minutes)
    _write_autopilot_state(path, payload)
    return payload


def _write_autopilot_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical(state), encoding="utf-8")


def _task_index(tasks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(task.get("task_id", "")): task for task in tasks}


def _next_actionable(tasks: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    index = _task_index(tasks)
    candidates: List[Dict[str, Any]] = []
    for task in tasks:
        if task.get("status") != "planned":
            continue
        deps = [str(dep) for dep in task.get("dependencies", [])]
        blocked = False
        for dep in deps:
            dep_task = index.get(dep)
            if not dep_task or dep_task.get("status") != "done":
                blocked = True
                break
        if not blocked:
            candidates.append(task)
    if not candidates:
        return None
    candidates.sort(
        key=lambda row: (
            int(row.get("priority", 99)),
            str(row.get("planned_start", "")),
            str(row.get("task_id", "")),
        )
    )
    return candidates[0]


def cmd_tick(
    *,
    state_path: Path,
    events_path: Path,
    autopilot_path: Path,
    interval_minutes: int,
    timeout_minutes: int,
) -> int:
    program = _read_program_state(state_path)
    autopilot = _read_or_init_autopilot_state(autopilot_path, interval_minutes, timeout_minutes)
    now = datetime.now(timezone.utc)
    now_iso = utc_now_iso()

    if not bool(autopilot.get("enabled", True)):
        autopilot["last_tick_at"] = now_iso
        autopilot["updated_at"] = now_iso
        autopilot["last_action"] = "disabled_noop"
        _write_autopilot_state(autopilot_path, autopilot)
        print(_canonical({"status": "ok", "action": "disabled_noop"}))
        return 0

    last_ack = _parse_iso(autopilot.get("last_user_ack_at"))
    timeout = timedelta(minutes=int(autopilot.get("no_response_timeout_minutes", timeout_minutes)))
    no_response = (last_ack is None) or (now - last_ack >= timeout)

    tasks = [dict(task) for task in program.get("tasks", []) if isinstance(task, dict)]
    active = [task for task in tasks if task.get("status") == "active"]

    action = "wait_for_response"
    changed_task = None

    if no_response:
        if active:
            action = "continue_active"
            append_program_event(
                events_path,
                event_type="autopilot_tick",
                summary="No user response; continuing active task(s)",
                payload={"active_task_ids": [task.get("task_id") for task in active]},
            )
        else:
            candidate = _next_actionable(tasks)
            if candidate is not None:
                candidate["status"] = "active"
                candidate["note"] = f"autopilot activated at {now_iso} after no response timeout"
                changed_task = str(candidate.get("task_id"))
                action = "activated_next_task"
                program["tasks"] = tasks
                program["updated_at"] = now_iso
                program["state_hash"] = compute_state_hash(program)
                write_program_state(state_path, program)
                append_program_event(
                    events_path,
                    event_type="autopilot_advance",
                    summary=f"Auto-activated next actionable task {changed_task}",
                    payload={"task_id": changed_task},
                )
            else:
                action = "no_actionable_task"
                append_program_event(
                    events_path,
                    event_type="autopilot_idle",
                    summary="No response and no actionable planned tasks",
                    payload={},
                )

    autopilot["last_tick_at"] = now_iso
    autopilot["updated_at"] = now_iso
    autopilot["last_action"] = action
    _write_autopilot_state(autopilot_path, autopilot)
    print(
        _canonical(
            {
                "status": "ok",
                "action": action,
                "no_response": no_response,
                "changed_task": changed_task,
                "last_user_ack_at": autopilot.get("last_user_ack_at"),
                "last_tick_at": now_iso,
            }
        )
    )
    return 0


def cmd_ack(*, autopilot_path: Path, note: str) -> int:
    autopilot = _read_or_init_autopilot_state(autopilot_path, 3, 3)
    now_iso = utc_now_iso()
    autopilot["last_user_ack_at"] = now_iso
    autopilot["updated_at"] = now_iso
    autopilot["last_action"] = f"ack:{note}" if note else "ack"
    _write_autopilot_state(autopilot_path, autopilot)
    print(_canonical({"status": "ok", "ack_at": now_iso}))
    return 0


def cmd_status(*, autopilot_path: Path) -> int:
    autopilot = _read_or_init_autopilot_state(autopilot_path, 3, 3)
    print(_canonical(autopilot))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QSO XR autopilot checker and task auto-advance")
    parser.add_argument("--state-path", default=".codex/state/xr_program_state.json", help="Program state path")
    parser.add_argument("--events-path", default=".codex/state/xr_program_events.jsonl", help="Program event log path")
    parser.add_argument("--autopilot-path", default=".codex/state/xr_autopilot_state.json", help="Autopilot state path")
    parser.add_argument("--interval-minutes", type=int, default=3, help="Expected cron check interval")
    parser.add_argument("--timeout-minutes", type=int, default=3, help="No-response timeout before advancing")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tick", help="Run one autopilot check")
    ack_cmd = sub.add_parser("ack", help="Record user acknowledgement")
    ack_cmd.add_argument("--note", default="", help="Optional ack note")
    sub.add_parser("status", help="Show autopilot state")
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    state_path = Path(args.state_path)
    events_path = Path(args.events_path)
    autopilot_path = Path(args.autopilot_path)
    if args.command == "tick":
        return cmd_tick(
            state_path=state_path,
            events_path=events_path,
            autopilot_path=autopilot_path,
            interval_minutes=int(args.interval_minutes),
            timeout_minutes=int(args.timeout_minutes),
        )
    if args.command == "ack":
        return cmd_ack(autopilot_path=autopilot_path, note=str(args.note))
    if args.command == "status":
        return cmd_status(autopilot_path=autopilot_path)
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
