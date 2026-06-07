# QSO XR Program Management

This framework now includes a built-in developer scheduling layer for Codex-led execution.

## Purpose

- Maintain a deterministic roadmap of milestones and tasks.
- Keep an append-only event log of scheduling actions.
- Provide CLI surfaces to inspect, prioritize, and advance work.

## State Artifacts

- Program state: `.codex/state/xr_program_state.json`
- Program events: `.codex/state/xr_program_events.jsonl`

## CLI

Use `qso-xr-program` (or `python -m tools.qso_xr_program`):

```bash
qso-xr-program init
qso-xr-program status
qso-xr-program next --limit 5
qso-xr-program set-status --task-id XR-T-002 --status active --note "Bridge contract implementation started"
```

## Scheduling Model

- Milestones are date-windowed and carry explicit success criteria.
- Tasks are dependency-aware and include validation commands.
- `next` returns only actionable tasks: status in `planned|active` with dependencies already `done`.

## Governance

- Milestone and task templates live in `qso_xr/program_management.py`.
- State changes are event-sourced in JSONL with hash chaining.
- Snapshot/artifact naming follows the `snapshot` vs `snapshots` contract in `docs/snapshot_nomenclature.md`.
