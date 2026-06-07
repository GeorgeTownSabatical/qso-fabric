from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from mcp_qso_edu.server import QSOEduMCPServer


ROOT = Path(__file__).resolve().parents[1]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qso-edu-apc-bootstrap",
        description="Generate APC educational artifact bundles without JSON-RPC.",
    )
    parser.add_argument("--session-token", default="apc-community", help="Session token used for sandbox derivation.")
    parser.add_argument("--sandbox-id", default="", help="Optional sandbox id assertion; must match token-derived id.")
    parser.add_argument(
        "--mode",
        choices=["quick", "standard", "exhaustive"],
        default="exhaustive",
        help="Bundle depth.",
    )
    parser.add_argument("--domain", default="physics", help="Scientific domain label.")
    parser.add_argument("--owner", default="community", help="Bundle owner label.")
    parser.add_argument(
        "--baseline-model",
        action="append",
        default=[],
        help="Baseline model for comparison harness; repeat flag to add many.",
    )
    parser.add_argument(
        "--baseline-models-csv",
        default="",
        help="Comma-separated baseline models; merged with --baseline-model values.",
    )
    parser.add_argument(
        "--state-root",
        default=".codex/state/mcp_qso_edu/sandboxes",
        help="Sandbox persistence root.",
    )
    parser.add_argument(
        "--apc-state-root",
        default=".codex/state/mcp_qso_edu/apc_fabric_edu",
        help="APC run state root.",
    )
    parser.add_argument(
        "--publish-dir",
        default="",
        help="Optional publish destination. Bundle is copied here as run_<id>/.",
    )
    parser.add_argument(
        "--json-output",
        default="",
        help="Optional path for machine-readable result JSON.",
    )
    return parser


def _abs(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    return path


def _normalize_baselines(explicit: list[str], csv_values: str) -> list[str]:
    values: list[str] = []
    for item in explicit:
        value = str(item).strip()
        if value:
            values.append(value)
    if csv_values.strip():
        for item in csv_values.split(","):
            value = item.strip()
            if value:
                values.append(value)
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    if not deduped:
        return ["LambdaCDM+SM", "EFT-agnostic baseline"]
    return deduped


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(argv: list[str] | None = None) -> dict[str, Any]:
    args = _build_parser().parse_args(argv)

    state_root = _abs(args.state_root)
    apc_state_root = _abs(args.apc_state_root)
    baselines = _normalize_baselines(list(args.baseline_model), str(args.baseline_models_csv))

    server = QSOEduMCPServer(
        state_root=state_root,
        apc_state_root=apc_state_root,
    )
    created = server.create_sandbox(str(args.session_token))
    sandbox_id = str(created["sandbox_id"])
    requested_sandbox = str(args.sandbox_id).strip()
    if requested_sandbox and requested_sandbox != sandbox_id:
        raise SystemExit(
            f"sandbox-id mismatch: provided={requested_sandbox} token-derived={sandbox_id}"
        )

    result = server.qso_edu_apc_bootstrap(
        sandbox_id,
        mode=str(args.mode),
        domain=str(args.domain),
        baseline_models=baselines,
        owner=str(args.owner),
    )
    payload = dict(result["result"])

    run_path = _abs(str(payload["run_path"]))
    published_path: Path | None = None
    if str(args.publish_dir).strip():
        publish_root = _abs(str(args.publish_dir))
        publish_root.mkdir(parents=True, exist_ok=True)
        published_path = publish_root / run_path.name
        shutil.copytree(run_path, published_path, dirs_exist_ok=True)

    output = {
        "ok": True,
        "sandbox_id": sandbox_id,
        "session_token": str(args.session_token),
        "mode": str(args.mode),
        "domain": str(args.domain),
        "owner": str(args.owner),
        "baseline_models": baselines,
        "run_path": str(run_path),
        "published_path": None if published_path is None else str(published_path),
        "artifact_count": payload.get("artifact_count"),
        "manifest": payload.get("manifest"),
        "speculative_status": payload.get("speculative_status"),
    }
    if str(args.json_output).strip():
        _write_json(_abs(str(args.json_output)), output)
    return output


def main(argv: list[str] | None = None) -> None:
    result = run(argv)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1:])
