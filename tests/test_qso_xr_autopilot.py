from __future__ import annotations

import json
from pathlib import Path

from tools.qso_xr_autopilot import main
from tools.qso_xr_program import main as program_main


def test_autopilot_tick_advances_next_task_when_no_active(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    state = tmp_path / "state.json"
    events = tmp_path / "events.jsonl"
    autopilot = tmp_path / "autopilot.json"

    assert program_main(["--state-path", str(state), "--events-path", str(events), "init"]) == 0
    capsys.readouterr()

    assert main(
        [
            "--state-path",
            str(state),
            "--events-path",
            str(events),
            "--autopilot-path",
            str(autopilot),
            "--timeout-minutes",
            "0",
            "tick",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] in {"activated_next_task", "continue_active"}

    program = json.loads(state.read_text(encoding="utf-8"))
    active = [task for task in program["tasks"] if task["status"] == "active"]
    assert len(active) >= 1


def test_autopilot_ack_updates_state(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    autopilot = tmp_path / "autopilot.json"
    assert main(["--autopilot-path", str(autopilot), "ack", "--note", "user responded"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    state = json.loads(autopilot.read_text(encoding="utf-8"))
    assert state["last_user_ack_at"] is not None
