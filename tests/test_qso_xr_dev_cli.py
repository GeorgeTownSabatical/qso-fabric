from __future__ import annotations

import json
from pathlib import Path

from tools.qso_xr_dev_cli import main


def test_qso_xr_dev_cli_packages_json(capsys) -> None:  # type: ignore[no-untyped-def]
    code = main(["packages", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["total_packages"] == 32
    assert len(payload["packages"]) == 32


def test_qso_xr_dev_cli_simulate_merge(capsys, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    code = main(
        [
            "simulate-merge",
            "--state-dir",
            str(tmp_path / "knowledge"),
            "--branch",
            "sandbox",
            "--claim",
            "entity.gamma|c1|claim text|0.75",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["approved"] is True
    assert payload["new_claims"] == 1


def test_qso_xr_dev_cli_demo_examples_seed(capsys, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    code = main(
        [
            "demo-examples",
            "--example",
            "image_2_torus_topology",
            "--seed",
            "--json",
            "--world-uri",
            "qso://xr.world/demo-seed",
            "--state-dir",
            str(tmp_path / "knowledge_demo"),
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["seed_result"]["example"] == "image_2_torus_topology"
    assert payload["seed_result"]["seeded_nodes"] >= 3


def test_qso_xr_dev_cli_export_qff_and_direct_scene(capsys, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    out_file = tmp_path / "cli_export.qff.json"
    code_export = main(
        [
            "export-qff",
            "--world-uri",
            "qso://xr.world/cli-export",
            "--state-dir",
            str(tmp_path / "knowledge_cli_export"),
            "--output",
            str(out_file),
            "--example",
            "image_1_shadow_throne",
            "--profile",
            "cinematic_low_light",
        ]
    )
    assert code_export == 0
    export_payload = json.loads(capsys.readouterr().out)
    assert export_payload["frame_hash"]
    assert out_file.exists()

    code_direct = main(
        [
            "direct-scene",
            "--world-uri",
            "qso://xr.world/cli-direct",
            "--state-dir",
            str(tmp_path / "knowledge_cli_direct"),
            "--objective",
            "preserve topology legend readability with fixed camera",
            "--profile",
            "analytic_educational",
        ]
    )
    assert code_direct == 0
    proposal = json.loads(capsys.readouterr().out)
    assert proposal["direct_mutation_allowed"] is False
    assert proposal["proposal_hash"]
