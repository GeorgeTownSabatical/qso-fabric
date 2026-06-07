from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from mcp_qso_edu.conversation_bridge import ConversationBridge
from mcp_qso_edu.sandbox_persistence import SandboxOperationStore
from services.transport.audit_logger import NetworkAuditLogger
from storage.event_store import JsonlEventStore

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".codex" / "state" / "mesh_smoke"


def _utc_ts_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if text.startswith("export "):
            text = text[len("export ") :]
        if "=" not in text:
            continue
        key, value = text.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def run_smoke(env_a: dict[str, str], env_b: dict[str, str]) -> dict[str, object]:
    event_store_a = JsonlEventStore(Path(env_a["QSO_EVENT_STORE_PATH"]))
    event_store_b = JsonlEventStore(Path(env_b["QSO_EVENT_STORE_PATH"]))
    event_store_a.append(
        {
            "event_id": f"mesh-smoke-a-{_utc_ts_compact()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": "mesh-instance-a",
            "object_uri": "qso://mesh/smoke",
            "delta": {"writer": "a"},
            "signature": "mesh-smoke",
            "policy_version": "v1",
            "node_id": "mesh-a",
        }
    )
    event_store_b.append(
        {
            "event_id": f"mesh-smoke-b-{_utc_ts_compact()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": "mesh-instance-b",
            "object_uri": "qso://mesh/smoke",
            "delta": {"writer": "b"},
            "signature": "mesh-smoke",
            "policy_version": "v1",
            "node_id": "mesh-b",
        }
    )
    event_chain_ok = JsonlEventStore(Path(env_a["QSO_EVENT_STORE_PATH"])).verify_chain()

    audit_a = NetworkAuditLogger(Path(env_a["QSO_NETWORK_AUDIT_PATH"]))
    audit_b = NetworkAuditLogger(Path(env_b["QSO_NETWORK_AUDIT_PATH"]))
    first_audit = audit_a.log(
        actor="mesh-instance-a",
        object_uri="qso://infra.transport",
        payload={"mode": "direct", "smoke": True},
        kind="mesh_smoke_audit",
        policy_version="v1",
    )
    second_audit = audit_b.log(
        actor="mesh-instance-b",
        object_uri="qso://infra.transport",
        payload={"mode": "direct", "smoke": True},
        kind="mesh_smoke_audit",
        policy_version="v1",
    )
    audit_chain_ok = NetworkAuditLogger(Path(env_a["QSO_NETWORK_AUDIT_PATH"])).verify_chain()

    bridge_a = ConversationBridge(Path(env_a["QSO_PLUS_BRIDGE_PATH"]))
    bridge_b = ConversationBridge(Path(env_b["QSO_PLUS_BRIDGE_PATH"]))
    bridge_first = bridge_a.append(source="mesh-instance-a", content="mesh-smoke-a", session_id="mesh")
    bridge_second = bridge_b.append(source="mesh-instance-b", content="mesh-smoke-b", session_id="mesh")
    bridge_chain_ok = bridge_second["prev_hash"] == bridge_first["hash"]

    sandbox_root_a = Path(env_a["QSO_SANDBOX_OP_ROOT"])
    sandbox_root_b = Path(env_b["QSO_SANDBOX_OP_ROOT"])
    sandbox_a = SandboxOperationStore(sandbox_root_a)
    sandbox_b = SandboxOperationStore(sandbox_root_b)
    sandbox_id = "mesh-smoke"
    sandbox_a.append_op(
        sandbox_id,
        {
            "op": "create",
            "uri": "qso://sandbox/mesh-smoke/object",
            "schema": {"kind": "mesh_smoke"},
        },
    )
    sandbox_b.append_op(
        sandbox_id,
        {
            "op": "patch",
            "uri": "qso://sandbox/mesh-smoke/object",
            "delta": {"status": "ok"},
            "actor": "mesh-instance-b",
        },
    )
    sandbox_rows = SandboxOperationStore(sandbox_root_a).read_ops(sandbox_id)
    sandbox_chain_ok = bool(sandbox_rows) and sandbox_rows[0].get("prev_hash") == "GENESIS"
    if len(sandbox_rows) >= 2:
        sandbox_chain_ok = sandbox_chain_ok and sandbox_rows[1].get("prev_hash") == sandbox_rows[0].get("hash")

    overall_ok = bool(event_chain_ok and audit_chain_ok and bridge_chain_ok and sandbox_chain_ok)
    return {
        "ok": overall_ok,
        "event_chain_ok": bool(event_chain_ok),
        "audit_chain_ok": bool(audit_chain_ok),
        "bridge_chain_ok": bool(bridge_chain_ok),
        "sandbox_chain_ok": bool(sandbox_chain_ok),
        "event_store_path": env_a["QSO_EVENT_STORE_PATH"],
        "audit_path": env_a["QSO_NETWORK_AUDIT_PATH"],
        "bridge_path": env_a["QSO_PLUS_BRIDGE_PATH"],
        "sandbox_root": env_a["QSO_SANDBOX_OP_ROOT"],
        "audit_prev_hash_linked": second_audit.get("prev_hash") == first_audit.get("hash"),
        "bridge_prev_hash_linked": bridge_second.get("prev_hash") == bridge_first.get("hash"),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a dual-writer smoke test across mesh env files.")
    parser.add_argument("--env-file-a", required=True)
    parser.add_argument("--env-file-b", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    env_a = _load_env_file(Path(args.env_file_a))
    env_b = _load_env_file(Path(args.env_file_b))
    result = run_smoke(env_a, env_b)

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = _utc_ts_compact()
    report_path = STATE_DIR / f"smoke_{run_id}.json"
    report = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "env_file_a": str(Path(args.env_file_a).resolve()),
        "env_file_b": str(Path(args.env_file_b).resolve()),
        "result": result,
    }
    report_path.write_text(json.dumps(report, sort_keys=True, indent=2), encoding="utf-8")
    print(str(report_path))
    print(json.dumps(result, sort_keys=True))
    return 0 if bool(result["ok"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
