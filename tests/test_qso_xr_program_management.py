from __future__ import annotations

import json
from pathlib import Path

from qso_xr.program_management import append_program_event, build_program_state, write_program_state


def test_build_program_state_has_milestones_tasks_and_hash() -> None:
    state = build_program_state()
    assert state["schema_version"] == "1.0"
    assert len(state["milestones"]) >= 5
    assert len(state["tasks"]) >= 10
    assert isinstance(state["state_hash"], str) and len(state["state_hash"]) == 64


def test_append_program_event_hash_chain(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    first = append_program_event(events, event_type="test", summary="first", payload={"n": 1})
    second = append_program_event(events, event_type="test", summary="second", payload={"n": 2})

    assert first["prev_hash"] == "GENESIS"
    assert second["prev_hash"] == first["hash"]

    rows = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 2


def test_write_program_state_roundtrip(tmp_path: Path) -> None:
    state = build_program_state()
    path = tmp_path / "state.json"
    write_program_state(path, state)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "1.0"
    assert loaded["program"]["name"] == "QSO XR Framework"
