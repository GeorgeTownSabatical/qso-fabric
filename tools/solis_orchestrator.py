from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from api.mcp_tools.qso_tools import QSOMCPTools
from api.rest import QSOIdentityRESTAPI, create_http_server
from solis.execution import load_replay_artifact, verify_replay_artifact
from solis.services.solis_star_service import SolisQSOBridge, SolisStarService
from solis.shared.hashing import sha256_hex_obj
from solis.strategy_dsl import compile_strategy_dsl


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


def _parse_delta(raw: str | None) -> dict[str, float]:
    if raw is None:
        return {}
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("--delta must deserialize to a JSON object")
    out: dict[str, float] = {}
    for key, value in loaded.items():
        out[str(key)] = float(value)
    return out


def _cmd_run(args: argparse.Namespace) -> int:
    service = SolisStarService()
    created = service.create_star(
        star_id=str(args.star_id),
        chain_id=str(args.chain_id),
        actor=str(args.actor),
    )
    delta = _parse_delta(args.delta)
    patched: dict[str, Any] | None = None
    if delta:
        patched = service.patch_star(
            star_uri_or_id=str(args.star_id),
            delta=delta,
            actor=str(args.actor),
        )
    _print_json(
        {
            "command": "run",
            "star_uri": service.star_uri(str(args.star_id)),
            "created_state_hash": sha256_hex_obj(created.get("state_layer", {})),
            "patched": patched is not None,
        }
    )
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    service = SolisStarService()
    uri = service.star_uri(str(args.star_id))
    if not service.qso.has(uri):
        service.create_star(star_id=str(args.star_id), chain_id=str(args.chain_id), actor=str(args.actor))
    timeline = service.qso.timeline(uri, strict=True)
    _print_json(
        {
            "command": "replay",
            "star_uri": uri,
            "event_count": len(timeline),
            "timeline_hash": sha256_hex_obj(timeline),
        }
    )
    return 0


def _cmd_shadow(args: argparse.Namespace) -> int:
    if bool(args.dsl_text) == bool(args.dsl_file):
        raise ValueError("provide exactly one of --dsl-text or --dsl-file")

    if args.dsl_file:
        text = Path(str(args.dsl_file)).read_text(encoding="utf-8")
    else:
        text = str(args.dsl_text)

    graph, graph_hash = compile_strategy_dsl(text)
    _print_json(
        {
            "command": "shadow",
            "graph_hash": graph_hash,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        }
    )
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    tools = QSOMCPTools()
    if args.uri:
        uri = str(args.uri)
        obj = tools.qso_read(uri)
        state = obj.get("state_layer", {})
        timeline = tools.qso_timeline(uri, strict=True)
        _print_json(
            {
                "command": "audit",
                "uri": uri,
                "state_hash": sha256_hex_obj(state),
                "event_count": len(timeline),
            }
        )
        return 0

    policy = tools.qso_policy_current()
    _print_json(
        {
            "command": "audit",
            "policy_version": str(policy.get("version", "")),
            "policy_hash": sha256_hex_obj(policy),
        }
    )
    return 0


def _ensure_export_uri(tools: QSOMCPTools, uri: str, create_if_missing: bool, chain_id: str, actor: str) -> None:
    if tools.runtime.registry.has(uri):
        return
    if not create_if_missing:
        raise ValueError(f"uri not found: {uri}")

    if uri.startswith("qso://solis.star."):
        star_id = uri.rsplit(".", 1)[-1]
        bridge = SolisQSOBridge(tools=tools)
        SolisStarService(qso=bridge).create_star(star_id=star_id, chain_id=chain_id, actor=actor)
        return

    tools.qso_create(uri, {"type": "export_seed"})
    tools.qso_patch(uri, {"seeded": True}, actor=actor, policy_version="v1", node_id="orchestrator")


def _cmd_export(args: argparse.Namespace) -> int:
    tools = QSOMCPTools()
    uri = str(args.uri)
    _ensure_export_uri(
        tools=tools,
        uri=uri,
        create_if_missing=bool(args.create_if_missing),
        chain_id=str(args.chain_id),
        actor=str(args.actor),
    )
    blob = tools.qso_export_snapshot(uri)
    out_path = Path(str(args.out))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(blob)
    _print_json(
        {
            "command": "export",
            "uri": uri,
            "out": str(out_path),
            "bytes": len(blob),
            "blob_hash": sha256_hex_obj({"blob_hex": blob.hex()}),
        }
    )
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    artifact = load_replay_artifact(Path(str(args.path)))
    ok = verify_replay_artifact(artifact)
    _print_json(
        {
            "command": "verify",
            "path": str(args.path),
            "artifact_hash": str(artifact.get("artifact_hash", "")),
            "verified": ok,
        }
    )
    return 0 if ok else 1


def _cmd_serve(args: argparse.Namespace) -> int:
    if bool(args.dry_run):
        _print_json(
            {
                "command": "serve",
                "host": str(args.host),
                "port": int(args.port),
                "dry_run": True,
            }
        )
        return 0

    api = QSOIdentityRESTAPI()
    server = create_http_server(host=str(args.host), port=int(args.port), api=api)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solis orchestrator CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Create and optionally patch a Solis star")
    run_cmd.add_argument("--star-id", default="spherechain")
    run_cmd.add_argument("--chain-id", default="spherechain")
    run_cmd.add_argument("--delta", default=None, help="JSON object of numeric patch deltas")
    run_cmd.add_argument("--actor", default="solis.orchestrator")
    run_cmd.set_defaults(handler=_cmd_run)

    replay_cmd = sub.add_parser("replay", help="Emit deterministic replay hash for a Solis star timeline")
    replay_cmd.add_argument("--star-id", default="spherechain")
    replay_cmd.add_argument("--chain-id", default="spherechain")
    replay_cmd.add_argument("--actor", default="solis.orchestrator")
    replay_cmd.set_defaults(handler=_cmd_replay)

    shadow_cmd = sub.add_parser("shadow", help="Compile strategy DSL in shadow mode (no execution)")
    shadow_cmd.add_argument("--dsl-text", default=None, help="Inline DSL source")
    shadow_cmd.add_argument("--dsl-file", default=None, help="Path to DSL file")
    shadow_cmd.set_defaults(handler=_cmd_shadow)

    audit_cmd = sub.add_parser("audit", help="Emit audit summary for a URI or current policy")
    audit_cmd.add_argument("--uri", default=None)
    audit_cmd.set_defaults(handler=_cmd_audit)

    export_cmd = sub.add_parser("export", help="Export QSO snapshot artifact")
    export_cmd.add_argument("--uri", required=True)
    export_cmd.add_argument("--out", required=True)
    export_cmd.add_argument("--create-if-missing", action="store_true")
    export_cmd.add_argument("--chain-id", default="spherechain")
    export_cmd.add_argument("--actor", default="solis.orchestrator")
    export_cmd.set_defaults(handler=_cmd_export)

    verify_cmd = sub.add_parser("verify", help="Verify an Alpaca replay artifact file")
    verify_cmd.add_argument("--path", required=True)
    verify_cmd.set_defaults(handler=_cmd_verify)

    serve_cmd = sub.add_parser("serve", help="Run Solis HTTP transport server")
    serve_cmd.add_argument("--host", default="0.0.0.0")
    serve_cmd.add_argument("--port", type=int, default=8000)
    serve_cmd.add_argument("--dry-run", action="store_true", help="Validate serve config without binding a socket")
    serve_cmd.set_defaults(handler=_cmd_serve)

    return parser


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.error("internal error: missing handler")
    try:
        return int(handler(args))
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
