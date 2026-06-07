from __future__ import annotations

import json
from pathlib import Path

from tools.qso_edu_apc_bootstrap import run


def test_qso_edu_apc_bootstrap_generates_bundle_and_json(tmp_path: Path) -> None:
    output_json = tmp_path / "result.json"
    result = run(
        [
            "--session-token",
            "cli-apc",
            "--mode",
            "quick",
            "--state-root",
            str(tmp_path / "sandboxes"),
            "--apc-state-root",
            str(tmp_path / "apc"),
            "--json-output",
            str(output_json),
        ]
    )

    run_path = Path(result["run_path"])
    assert result["ok"] is True
    assert run_path.exists()
    assert (run_path / "manifest.json").exists()
    assert int(result["artifact_count"]) >= 10
    assert (run_path / "validation" / "apc_bayes_comparison_latest.json").exists()
    assert output_json.exists()

    persisted = json.loads(output_json.read_text(encoding="utf-8"))
    assert persisted["run_path"] == result["run_path"]
    assert persisted["speculative_status"] == "unvalidated_hypothesis"


def test_qso_edu_apc_bootstrap_publish_dir_copies_bundle(tmp_path: Path) -> None:
    publish_dir = tmp_path / "published"
    result = run(
        [
            "--session-token",
            "cli-apc-publish",
            "--mode",
            "quick",
            "--state-root",
            str(tmp_path / "sandboxes"),
            "--apc-state-root",
            str(tmp_path / "apc"),
            "--publish-dir",
            str(publish_dir),
            "--baseline-model",
            "Baseline-A",
            "--baseline-models-csv",
            "Baseline-B,Baseline-C",
        ]
    )

    published_path = Path(str(result["published_path"]))
    assert published_path.exists()
    assert (published_path / "manifest.json").exists()
    assert (published_path / "validation" / "apc_bayes_comparison_latest.json").exists()
    assert result["baseline_models"] == ["Baseline-A", "Baseline-B", "Baseline-C"]
