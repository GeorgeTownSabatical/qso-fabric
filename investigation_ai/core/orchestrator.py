"""Orchestrates ingestion, reasoning, and autonomous hypothesis cycles."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from core.service_config import AUTO_REPO, OUT, PROPERTY_REPO, REASONING_REPO


def _run(cmd: list[str], cwd: Path) -> dict:
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    return {
        "cmd": cmd,
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def run_stack_once() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)

    ingest = _run(["python3", "run_global_graph.py"], PROPERTY_REPO)
    reason = _run(
        [
            "python3",
            "pipeline/reasoning_pipeline.py",
            "--graph-json",
            str(PROPERTY_REPO / "data" / "outputs" / "global_graph.json"),
            "--output-dir",
            str(REASONING_REPO / "data" / "outputs"),
        ],
        REASONING_REPO,
    )
    hypo = _run(
        [
            "python3",
            "pipeline/autonomous_cycle.py",
            "--graph-json",
            str(PROPERTY_REPO / "data" / "outputs" / "global_graph.json"),
            "--reasoning-dir",
            str(REASONING_REPO / "data" / "outputs"),
            "--output-dir",
            str(AUTO_REPO / "data" / "outputs"),
            "--max-cycles",
            "1",
        ],
        AUTO_REPO,
    )

    summary = {
        "ingestion_ok": ingest["returncode"] == 0,
        "reasoning_ok": reason["returncode"] == 0,
        "hypothesis_ok": hypo["returncode"] == 0,
        "steps": {
            "ingestion": ingest,
            "reasoning": reason,
            "hypothesis": hypo,
        },
    }
    (OUT / "stack_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
