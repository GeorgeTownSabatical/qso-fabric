from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, List

from core.naming.snapshot_terms import resolve_snapshot_artifact_path
from qso_xr.demo_examples import get_demo_example, list_demo_examples
from qso_xr.knowledge_lattice import KnowledgeLattice
from qso_xr.package_registry import coverage_summary, list_packages
from qso_xr.runtime import QSOXRRuntime


def _canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _parse_claim(value: str) -> dict[str, Any]:
    parts = value.split("|", 3)
    if len(parts) != 4:
        raise ValueError("claim format must be section|claim_id|statement|confidence")
    section, claim_id, statement, confidence_raw = parts
    confidence = float(confidence_raw)
    return {
        "section": section.strip(),
        "claim_id": claim_id.strip(),
        "statement": statement.strip(),
        "confidence": confidence,
    }


def _cmd_packages(as_json: bool) -> int:
    rows = list_packages()
    if as_json:
        payload = {
            "summary": coverage_summary(),
            "packages": [
                {
                    "package": row.package,
                    "section": row.section,
                    "purpose": row.purpose,
                    "implemented": row.implemented,
                    "module": row.module,
                    "dependencies": list(row.dependencies),
                }
                for row in rows
            ],
        }
        print(_canonical(payload))
        return 0

    summary = coverage_summary()
    print(f"total={summary['total_packages']} implemented={summary['implemented_count']} scaffolded={summary['scaffolded_count']}")
    for row in rows:
        status = "implemented" if row.implemented else "scaffolded"
        print(f"{row.package}\t{status}\t{row.module or '-'}")
    return 0


def _cmd_merge(state_dir: Path, branch: str, claim_rows: List[str], vote_approved: bool) -> int:
    lattice = KnowledgeLattice(state_dir)
    claims = [_parse_claim(row) for row in claim_rows]
    report = lattice.merge_sandbox(branch_name=branch, claims=claims, vote_approved=vote_approved)
    print(_canonical(report))
    return 0


def _cmd_status(world_uri: str, state_dir: Path) -> int:
    runtime = QSOXRRuntime(world_uri=world_uri, knowledge_state_dir=state_dir)
    print(_canonical(runtime.status()))
    return 0


def _cmd_export_qff(
    *,
    world_uri: str,
    state_dir: Path,
    output: Path,
    example: str | None,
    profile: str | None,
) -> int:
    runtime = QSOXRRuntime(world_uri=world_uri, knowledge_state_dir=state_dir)
    selected_profile = profile
    if example:
        seeded = runtime.apply_demo_example(example)
        selected_profile = selected_profile or str(seeded.get("profile", "default"))
    out = runtime.export_qff(path=output, profile=selected_profile)
    print(_canonical(out))
    return 0


def _cmd_direct_scene(
    *,
    world_uri: str,
    state_dir: Path,
    objective: str,
    profile: str,
    max_patches: int,
) -> int:
    runtime = QSOXRRuntime(world_uri=world_uri, knowledge_state_dir=state_dir)
    proposal = runtime.propose_scene_direction(
        objective=objective,
        profile=profile,
        max_patches=max_patches,
    )
    print(_canonical(proposal))
    return 0


def _cmd_arkit_roundtrip(
    *,
    world_uri: str,
    state_dir: Path,
    input_json: Path,
) -> int:
    frame = json.loads(input_json.read_text(encoding="utf-8"))
    if not isinstance(frame, dict):
        raise ValueError("ARKit input JSON must be object")
    runtime = QSOXRRuntime(world_uri=world_uri, knowledge_state_dir=state_dir)
    imported = runtime.import_arkit_frame(frame)
    exported = runtime.export_arkit_scene()
    print(_canonical({"imported": imported, "exported": exported}))
    return 0


def _cmd_demo_examples(as_json: bool, example: str | None, seed: bool, world_uri: str, state_dir: Path) -> int:
    if not example:
        payload = {"examples": list_demo_examples()}
        if as_json:
            print(_canonical(payload))
        else:
            for item in payload["examples"]:
                print(item)
        return 0

    demo = get_demo_example(example)
    if not seed:
        if as_json:
            print(_canonical(demo))
        else:
            print(f"{example}: {demo['title']}")
            for need in demo.get("distinct_needs", []):
                print(f"- {need}")
        return 0

    runtime = QSOXRRuntime(world_uri=world_uri, knowledge_state_dir=state_dir)
    seeded = runtime.apply_demo_example(example)
    output = {"example": demo, "seed_result": seeded, "status": runtime.status()}
    print(_canonical(output))
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QSO XR developer CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    packages_cmd = sub.add_parser("packages", help="Show package coverage")
    packages_cmd.add_argument("--json", action="store_true", help="Emit JSON payload")

    merge_cmd = sub.add_parser("simulate-merge", help="Run deterministic sandbox knowledge merge")
    merge_cmd.add_argument("--state-dir", default=".codex/state/xr_knowledge", help="Knowledge state directory")
    merge_cmd.add_argument("--branch", default="sandbox", help="Branch label")
    merge_cmd.add_argument("--claim", action="append", default=[], help="Claim row: section|claim_id|statement|confidence")
    merge_cmd.add_argument("--deny", action="store_true", help="Reject merge vote (fail closed on conflicts)")

    status_cmd = sub.add_parser("status", help="Runtime + package status summary")
    status_cmd.add_argument("--world-uri", default="qso://xr.world/default", help="World URI")
    status_cmd.add_argument("--state-dir", default=".codex/state/xr_knowledge", help="Knowledge state directory")

    demo_cmd = sub.add_parser("demo-examples", help="Inspect or seed image-based demo examples")
    demo_cmd.add_argument("--example", default="", help="Example id to inspect/seed")
    demo_cmd.add_argument("--seed", action="store_true", help="Apply example to runtime and emit status")
    demo_cmd.add_argument("--json", action="store_true", help="Emit JSON payload")
    demo_cmd.add_argument("--world-uri", default="qso://xr.world/demo", help="World URI for seeding")
    demo_cmd.add_argument("--state-dir", default=".codex/state/xr_knowledge_demo", help="Knowledge state directory")

    export_cmd = sub.add_parser("export-qff", help="Export deterministic XR QFF JSON artifact")
    export_cmd.add_argument("--world-uri", default="qso://xr.world/export", help="World URI")
    export_cmd.add_argument("--state-dir", default=".codex/state/xr_knowledge_export", help="Knowledge state directory")
    export_cmd.add_argument(
        "--output",
        default=str(resolve_snapshot_artifact_path("qso_xr_export.qff.json")),
        help="Output QFF JSON path",
    )
    export_cmd.add_argument("--example", default="", help="Optional demo example to seed before export")
    export_cmd.add_argument("--profile", default="", help="Optional explicit profile label")

    director_cmd = sub.add_parser("direct-scene", help="Generate deterministic scene-direction proposal")
    director_cmd.add_argument("--world-uri", default="qso://xr.world/director", help="World URI")
    director_cmd.add_argument("--state-dir", default=".codex/state/xr_knowledge_director", help="Knowledge state directory")
    director_cmd.add_argument("--objective", required=True, help="Scene objective text")
    director_cmd.add_argument("--profile", default="default", help="Profile label")
    director_cmd.add_argument("--max-patches", type=int, default=3, help="Maximum proposed patches")

    arkit_cmd = sub.add_parser("arkit-roundtrip", help="Import ARKit frame JSON into runtime and export back out")
    arkit_cmd.add_argument("--world-uri", default="qso://xr.world/arkit", help="World URI")
    arkit_cmd.add_argument("--state-dir", default=".codex/state/xr_knowledge_arkit", help="Knowledge state directory")
    arkit_cmd.add_argument("--input-json", required=True, help="Input ARKit frame JSON path")

    args = parser.parse_args(argv)
    if args.command == "packages":
        return _cmd_packages(as_json=bool(args.json))
    if args.command == "simulate-merge":
        return _cmd_merge(
            state_dir=Path(args.state_dir),
            branch=str(args.branch),
            claim_rows=list(args.claim),
            vote_approved=not bool(args.deny),
        )
    if args.command == "status":
        return _cmd_status(world_uri=str(args.world_uri), state_dir=Path(args.state_dir))
    if args.command == "demo-examples":
        selected = str(args.example).strip() or None
        return _cmd_demo_examples(
            as_json=bool(args.json),
            example=selected,
            seed=bool(args.seed),
            world_uri=str(args.world_uri),
            state_dir=Path(args.state_dir),
        )
    if args.command == "export-qff":
        selected = str(args.example).strip() or None
        profile = str(args.profile).strip() or None
        return _cmd_export_qff(
            world_uri=str(args.world_uri),
            state_dir=Path(args.state_dir),
            output=Path(args.output),
            example=selected,
            profile=profile,
        )
    if args.command == "direct-scene":
        return _cmd_direct_scene(
            world_uri=str(args.world_uri),
            state_dir=Path(args.state_dir),
            objective=str(args.objective),
            profile=str(args.profile),
            max_patches=int(args.max_patches),
        )
    if args.command == "arkit-roundtrip":
        return _cmd_arkit_roundtrip(
            world_uri=str(args.world_uri),
            state_dir=Path(args.state_dir),
            input_json=Path(str(args.input_json)),
        )
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
