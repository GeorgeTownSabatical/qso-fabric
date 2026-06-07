from __future__ import annotations

from pathlib import Path

from tools.solis_task_manifest import (
    DEFAULT_MANIFEST_PATH,
    load_manifest,
    ready_tasks,
    topological_order,
    validate_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / DEFAULT_MANIFEST_PATH


def test_master_manifest_valid_and_acyclic() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    errors = validate_manifest(manifest)
    assert errors == []

    ordered = topological_order(manifest)
    task_ids = [str(task["id"]) for task in manifest["tasks"]]
    assert len(ordered) == len(task_ids)
    assert set(ordered) == set(task_ids)


def test_ready_tasks_only_include_dependency_satisfied_planned_work() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    tasks = {str(task["id"]): task for task in manifest["tasks"]}
    ready = ready_tasks(manifest)
    ready_ids = {str(task["id"]) for task in ready}

    assert "T0001" in ready_ids
    assert "T1002" in ready_ids
    assert "T1001" not in ready_ids  # done
    assert "T0202" not in ready_ids  # done
    assert "T0206" not in ready_ids  # done
    assert "T0402" not in ready_ids  # blocked by unfinished dependencies

    for task in ready:
        task_id = str(task["id"])
        status = str(task["status"])
        assert status in {"planned", "in_progress"}
        for dep in task["depends_on"]:
            assert str(tasks[str(dep)]["status"]) == "done", f"{task_id} listed as ready before {dep} is done"
