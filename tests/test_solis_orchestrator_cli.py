from __future__ import annotations

from pathlib import Path

from solis.execution import build_replay_artifact, write_replay_artifact
from tools.solis_orchestrator import _build_parser, run


def test_orchestrator_help_lists_required_subcommands() -> None:
    parser = _build_parser()
    help_text = parser.format_help()
    for name in ("run", "replay", "shadow", "audit", "export", "verify", "serve"):
        assert name in help_text


def test_orchestrator_shadow_and_serve_dry_run_commands() -> None:
    dsl = "\n".join(
        [
            "agent alpha",
            "version v1",
            "assets:",
            "BTC",
            "ETH",
            "allocation:",
            "BTC 60%",
            "ETH 40%",
            "rebalance interval 1d",
            "risk:",
            "max_drawdown 3%",
            "collapse_threshold 0.7",
            "no_margin true",
        ]
    )
    assert run(["shadow", "--dsl-text", dsl]) == 0
    assert run(["serve", "--dry-run", "--host", "127.0.0.1", "--port", "8111"]) == 0


def test_orchestrator_run_replay_audit_export_verify(tmp_path: Path) -> None:
    assert run(
        [
            "run",
            "--star-id",
            "cli_star",
            "--chain-id",
            "spherechain",
            "--delta",
            '{"mass": 0.25, "entropy_index": 0.03}',
        ]
    ) == 0
    assert run(["replay", "--star-id", "cli_star"]) == 0
    assert run(["audit"]) == 0

    export_path = tmp_path / "cli_star.qff"
    assert run(
        [
            "export",
            "--uri",
            "qso://solis.star.cli_export",
            "--out",
            str(export_path),
            "--create-if-missing",
        ]
    ) == 0
    assert export_path.exists()
    assert export_path.stat().st_size > 0

    replay_artifact = build_replay_artifact(
        [
            {"event_id": "alpaca-event-000001", "operation": "get_account", "status_code": 200},
            {"event_id": "alpaca-event-000002", "operation": "get_clock", "status_code": 200},
        ],
        base_url="https://paper-api.alpaca.markets",
        scenario="test",
    )
    artifact_path = tmp_path / "alpaca_replay.json"
    write_replay_artifact(artifact_path, replay_artifact)
    assert run(["verify", "--path", str(artifact_path)]) == 0
