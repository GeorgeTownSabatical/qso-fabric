from __future__ import annotations

import json
from pathlib import Path

from tools.qso_xr_program import main


def test_program_cli_init_status_next_and_set_status(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    state = tmp_path / "xr_program_state.json"
    events = tmp_path / "xr_program_events.jsonl"

    rc = main(["--state-path", str(state), "--events-path", str(events), "init"])
    assert rc == 0
    init_payload = json.loads(capsys.readouterr().out)
    assert init_payload["status"] == "ok"
    assert state.exists()
    assert events.exists()

    rc = main(["--state-path", str(state), "status", "--json"])
    assert rc == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["counts"]["tasks_total"] >= 10

    rc = main(["--state-path", str(state), "next", "--limit", "3", "--json"])
    assert rc == 0
    next_payload = json.loads(capsys.readouterr().out)
    assert len(next_payload["tasks"]) >= 1
    task_id = str(next_payload["tasks"][0]["task_id"])

    rc = main(
        [
            "--state-path",
            str(state),
            "--events-path",
            str(events),
            "set-status",
            "--task-id",
            task_id,
            "--status",
            "active",
            "--note",
            "started from test",
        ]
    )
    assert rc == 0
    set_payload = json.loads(capsys.readouterr().out)
    assert set_payload["new_status"] == "active"
