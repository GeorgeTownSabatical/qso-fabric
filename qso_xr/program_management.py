from __future__ import annotations

import json
import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from qso_xr.package_registry import list_packages

PROGRAM_SCHEMA_VERSION = "1.0"
DEFAULT_SESSION_ID = "qso-xr-program-2026"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _milestones() -> List[Dict[str, Any]]:
    return [
        {
            "milestone_id": "M-001",
            "title": "Rendering Reliability",
            "window_start": "2026-03-02",
            "window_end": "2026-03-13",
            "success_criteria": [
                "WebGL/WebXR viewer stable on both canonical demos",
                "Deterministic frame-hash parity validated in CI",
            ],
            "status": "active",
        },
        {
            "milestone_id": "M-002",
            "title": "Interface Bridges",
            "window_start": "2026-03-16",
            "window_end": "2026-03-27",
            "success_criteria": [
                "Unity and Unreal bridge contracts implemented",
                "ARKit adapter baseline import/export path verified",
            ],
            "status": "planned",
        },
        {
            "milestone_id": "M-003",
            "title": "Physics + Identity Expansion",
            "window_start": "2026-03-30",
            "window_end": "2026-04-10",
            "success_criteria": [
                "Haptic and gesture engines integrated with avatar attestation",
                "Emotion field and NPC behavior deterministic replay coverage added",
            ],
            "status": "planned",
        },
        {
            "milestone_id": "M-004",
            "title": "Distributed XR Fabric",
            "window_start": "2026-04-13",
            "window_end": "2026-04-24",
            "success_criteria": [
                "Consensus + meta-learning scaffolds upgraded to executable services",
                "Edge and GPU runtime compatibility lane passing in CI",
            ],
            "status": "planned",
        },
        {
            "milestone_id": "M-005",
            "title": "Autonomy + Release Candidate",
            "window_start": "2026-04-27",
            "window_end": "2026-05-08",
            "success_criteria": [
                "Autonomous world evolver guarded by knowledge profile gates",
                "Release-candidate manifest and integration checks green",
            ],
            "status": "planned",
        },
    ]


def _task_templates() -> List[Dict[str, Any]]:
    return [
        {
            "task_id": "XR-T-001",
            "title": "Upgrade local viewer interactions and parity checks",
            "milestone_id": "M-001",
            "priority": 1,
            "kind": "refinement",
            "status": "done",
            "planned_start": "2026-02-26",
            "planned_end": "2026-02-26",
            "dependencies": [],
            "validation_commands": [
                "python -m tools.build_xr_demo_viewers",
                "pytest -q tests/test_webxr_adapter.py tests/test_qso_xr_determinism_pipeline.py",
            ],
        },
        {
            "task_id": "XR-T-002",
            "title": "Implement qso-apple-arkit-adapter baseline import/export",
            "milestone_id": "M-002",
            "priority": 1,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-03-16",
            "planned_end": "2026-03-19",
            "dependencies": [],
            "validation_commands": ["pytest -q tests -k arkit"],
        },
        {
            "task_id": "XR-T-003",
            "title": "Implement qso-unity-bridge contract and playback harness",
            "milestone_id": "M-002",
            "priority": 1,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-03-18",
            "planned_end": "2026-03-24",
            "dependencies": ["XR-T-002"],
            "validation_commands": ["pytest -q tests -k unity_bridge"],
        },
        {
            "task_id": "XR-T-004",
            "title": "Implement qso-unreal-bridge contract and playback harness",
            "milestone_id": "M-002",
            "priority": 1,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-03-20",
            "planned_end": "2026-03-27",
            "dependencies": ["XR-T-002"],
            "validation_commands": ["pytest -q tests -k unreal_bridge"],
        },
        {
            "task_id": "XR-T-005",
            "title": "Implement qso-haptic-feedback-engine runtime surface",
            "milestone_id": "M-003",
            "priority": 2,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-03-30",
            "planned_end": "2026-04-02",
            "dependencies": ["XR-T-003", "XR-T-004"],
            "validation_commands": ["pytest -q tests -k haptic"],
        },
        {
            "task_id": "XR-T-006",
            "title": "Implement qso-symbolic-gesture-parser deterministic parser",
            "milestone_id": "M-003",
            "priority": 2,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-03-31",
            "planned_end": "2026-04-04",
            "dependencies": ["XR-T-005"],
            "validation_commands": ["pytest -q tests -k gesture_parser"],
        },
        {
            "task_id": "XR-T-007",
            "title": "Implement qso-emotion-field-model deterministic affect vectors",
            "milestone_id": "M-003",
            "priority": 2,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-04-01",
            "planned_end": "2026-04-08",
            "dependencies": ["XR-T-006"],
            "validation_commands": ["pytest -q tests -k emotion_field"],
        },
        {
            "task_id": "XR-T-008",
            "title": "Implement qso-behavioral-npc-engine on top of emotion model",
            "milestone_id": "M-003",
            "priority": 1,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-04-02",
            "planned_end": "2026-04-10",
            "dependencies": ["XR-T-007"],
            "validation_commands": ["pytest -q tests -k npc_engine"],
        },
        {
            "task_id": "XR-T-009",
            "title": "Implement qso-xr-consensus-layer deterministic reconciliation",
            "milestone_id": "M-004",
            "priority": 1,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-04-13",
            "planned_end": "2026-04-17",
            "dependencies": [],
            "validation_commands": ["pytest -q tests -k xr_consensus"],
        },
        {
            "task_id": "XR-T-010",
            "title": "Implement qso-xr-global-meta-learning policy adaptation lane",
            "milestone_id": "M-004",
            "priority": 1,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-04-16",
            "planned_end": "2026-04-22",
            "dependencies": ["XR-T-009"],
            "validation_commands": ["pytest -q tests -k xr_meta_learning"],
        },
        {
            "task_id": "XR-T-011",
            "title": "Implement qso-gpu-kernel-runtime compatibility module",
            "milestone_id": "M-004",
            "priority": 2,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-04-14",
            "planned_end": "2026-04-21",
            "dependencies": [],
            "validation_commands": ["pytest -q tests -k gpu_runtime"],
        },
        {
            "task_id": "XR-T-012",
            "title": "Implement qso-edge-node-runtime deterministic deployment hooks",
            "milestone_id": "M-004",
            "priority": 2,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-04-15",
            "planned_end": "2026-04-24",
            "dependencies": ["XR-T-009"],
            "validation_commands": ["pytest -q tests -k edge_runtime"],
        },
        {
            "task_id": "XR-T-013",
            "title": "Implement qso-diffusion-3d deterministic asset proposal lane",
            "milestone_id": "M-005",
            "priority": 2,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-04-27",
            "planned_end": "2026-04-30",
            "dependencies": [],
            "validation_commands": ["pytest -q tests -k diffusion_3d"],
        },
        {
            "task_id": "XR-T-014",
            "title": "Implement qso-nerf-engine deterministic scene approximation lane",
            "milestone_id": "M-005",
            "priority": 2,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-04-28",
            "planned_end": "2026-05-02",
            "dependencies": ["XR-T-013"],
            "validation_commands": ["pytest -q tests -k nerf_engine"],
        },
        {
            "task_id": "XR-T-015",
            "title": "Implement qso-autonomous-world-evolver with profile gates",
            "milestone_id": "M-005",
            "priority": 1,
            "kind": "feature",
            "status": "planned",
            "planned_start": "2026-04-30",
            "planned_end": "2026-05-08",
            "dependencies": ["XR-T-010", "XR-T-014"],
            "validation_commands": ["pytest -q tests -k autonomous_world_evolver"],
        },
    ]


def build_program_state(*, session_id: str = DEFAULT_SESSION_ID) -> Dict[str, Any]:
    now = utc_now_iso()
    package_status = {
        spec.package: {
            "implemented": spec.implemented,
            "module": spec.module,
            "dependencies": list(spec.dependencies),
        }
        for spec in list_packages()
    }
    tasks = _task_templates()
    state = {
        "schema_version": PROGRAM_SCHEMA_VERSION,
        "session_id": session_id,
        "created_at": now,
        "updated_at": now,
        "owner": "codex",
        "program": {
            "name": "QSO XR Framework",
            "cadence": "weekly",
            "timezone": "UTC",
            "today": date.today().isoformat(),
        },
        "milestones": _milestones(),
        "tasks": tasks,
        "package_status": package_status,
        "state_hash": "",
    }
    state["state_hash"] = compute_state_hash(state)
    return state


def append_program_event(
    events_path: Path,
    *,
    event_type: str,
    summary: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    if events_path.exists():
        lines = [line for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        prev_hash = json.loads(lines[-1])["hash"] if lines else "GENESIS"
        seq = len(lines) + 1
    else:
        prev_hash = "GENESIS"
        seq = 1
    event = {
        "schema_version": PROGRAM_SCHEMA_VERSION,
        "event_id": f"xr-prog-ev-{seq:08d}",
        "ts": utc_now_iso(),
        "actor": "codex",
        "event_type": str(event_type),
        "summary": str(summary),
        "payload": dict(payload),
        "prev_hash": prev_hash,
    }
    event["hash"] = _sha256_hex(event)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(_canonical_json(event) + "\n")
    return event


def write_program_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(state), encoding="utf-8")


def compute_state_hash(state: Dict[str, Any]) -> str:
    material = {
        "schema_version": state.get("schema_version"),
        "session_id": state.get("session_id"),
        "program": state.get("program", {}),
        "milestones": state.get("milestones", []),
        "tasks": state.get("tasks", []),
        "package_status": state.get("package_status", {}),
    }
    return _sha256_hex(material)
