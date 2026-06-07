"""Worker-side task execution."""

from __future__ import annotations

from pathlib import Path
import subprocess


BASE = Path(__file__).resolve().parents[2]
INVESTIGATION_REPO = BASE / "investigation_ai"


def execute_task(task: dict) -> tuple[bool, dict]:
    task_type = task.get("task_type")

    if task_type == "ingestion":
        cmd = ["python3", "pipeline/run_ingestion.py", "--max-runs", "1"]
    elif task_type == "reasoning":
        cmd = ["python3", "pipeline/run_reasoning.py", "--max-runs", "1"]
    elif task_type == "hypothesis":
        cmd = ["python3", "pipeline/autonomous_cycle.py", "--max-runs", "1"]
    else:
        return False, {"error": f"unknown task_type: {task_type}"}

    proc = subprocess.run(cmd, cwd=str(INVESTIGATION_REPO), text=True, capture_output=True)
    return proc.returncode == 0, {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}
