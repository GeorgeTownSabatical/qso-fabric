from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.transport.audit_logger import NetworkAuditLogger
from storage.event_store import JsonlEventStore

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".codex" / "state" / "mesh_integrity"
LAST_STATUS_PATH = STATE_DIR / "last_status.json"
ALERTS_PATH = STATE_DIR / "alerts.jsonl"
RUNS_DIR = STATE_DIR / "runs"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _hash_row(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _verify_bridge(path: Path) -> tuple[bool, int, str]:
    if not path.exists():
        return False, 0, "missing"

    prev_hash = "GENESIS"
    last_seq = 0
    rows = 0
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            row = json.loads(text)
            seq = int(row.get("seq", 0))
            if seq <= last_seq:
                return False, rows, f"non_monotonic_seq_at_line_{idx}"
            if str(row.get("prev_hash", "")) != prev_hash:
                return False, rows, f"prev_hash_mismatch_at_line_{idx}"
            expected = _hash_row({k: v for k, v in row.items() if k != "hash"})
            if str(row.get("hash", "")) != expected:
                return False, rows, f"hash_mismatch_at_line_{idx}"
            prev_hash = expected
            last_seq = seq
            rows += 1
    return True, rows, "ok"


def _verify_sandbox_root(root: Path) -> tuple[bool, int, str]:
    if not root.exists():
        return False, 0, "missing"

    files = sorted(root.rglob("*.ops.jsonl"))
    checked_rows = 0
    for file_path in files:
        prev_hash = "GENESIS"
        with file_path.open("r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle, 1):
                text = line.strip()
                if not text:
                    continue
                row = json.loads(text)
                if str(row.get("prev_hash", "")) != prev_hash:
                    return False, checked_rows, f"prev_hash_mismatch:{file_path}:{idx}"
                expected = _hash_row({k: v for k, v in row.items() if k != "hash"})
                if str(row.get("hash", "")) != expected:
                    return False, checked_rows, f"hash_mismatch:{file_path}:{idx}"
                prev_hash = expected
                checked_rows += 1
    return True, checked_rows, "ok"


def _evaluate_instance(env_file: Path) -> dict[str, Any]:
    env = _load_env_file(env_file)
    event_path = Path(env["QSO_EVENT_STORE_PATH"])
    audit_path = Path(env["QSO_NETWORK_AUDIT_PATH"])
    bridge_path = Path(env["QSO_PLUS_BRIDGE_PATH"])
    sandbox_root = Path(env["QSO_SANDBOX_OP_ROOT"])

    event_chain_ok = JsonlEventStore(event_path).verify_chain() if event_path.exists() else False
    audit_chain_ok = NetworkAuditLogger(audit_path).verify_chain() if audit_path.exists() else False
    bridge_ok, bridge_rows, bridge_detail = _verify_bridge(bridge_path)
    sandbox_ok, sandbox_rows, sandbox_detail = _verify_sandbox_root(sandbox_root)

    overall_ok = bool(event_chain_ok and audit_chain_ok and bridge_ok and sandbox_ok)
    return {
        "env_file": str(env_file),
        "event_path": str(event_path),
        "audit_path": str(audit_path),
        "bridge_path": str(bridge_path),
        "sandbox_root": str(sandbox_root),
        "event_chain_ok": bool(event_chain_ok),
        "audit_chain_ok": bool(audit_chain_ok),
        "bridge_chain_ok": bool(bridge_ok),
        "bridge_rows": int(bridge_rows),
        "bridge_detail": bridge_detail,
        "sandbox_chain_ok": bool(sandbox_ok),
        "sandbox_rows": int(sandbox_rows),
        "sandbox_detail": sandbox_detail,
        "overall_ok": overall_ok,
        "checked_at": _utc_now_iso(),
    }


def _load_last_status() -> dict[str, Any]:
    if not LAST_STATUS_PATH.exists():
        return {}
    data = json.loads(LAST_STATUS_PATH.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    return {}


def _append_alert(record: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with ALERTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def _save_last_status(payload: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LAST_STATUS_PATH.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")


def _save_run_report(payload: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_path = RUNS_DIR / f"integrity_{_utc_ts_compact()}.json"
    run_path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    return run_path


def run(env_files: list[Path]) -> tuple[bool, Path]:
    previous = _load_last_status()
    rows = []
    alerts = []

    for env_file in env_files:
        key = str(env_file.resolve())
        current = _evaluate_instance(env_file)
        rows.append(current)

        prev_row = previous.get(key, {})
        prev_ok = prev_row.get("overall_ok")
        current_ok = current["overall_ok"]
        if prev_ok is not False and current_ok is False:
            alert = {
                "event": "mesh_divergence_detected",
                "ts": _utc_now_iso(),
                "env_file": key,
                "previous_overall_ok": prev_ok,
                "current_overall_ok": current_ok,
                "detail": {
                    "event_chain_ok": current["event_chain_ok"],
                    "audit_chain_ok": current["audit_chain_ok"],
                    "bridge_chain_ok": current["bridge_chain_ok"],
                    "sandbox_chain_ok": current["sandbox_chain_ok"],
                },
            }
            _append_alert(alert)
            alerts.append(alert)
        previous[key] = current

    _save_last_status(previous)
    overall_ok = all(bool(row["overall_ok"]) for row in rows)
    report = {
        "created_at": _utc_now_iso(),
        "overall_ok": overall_ok,
        "instances": rows,
        "alerts_emitted": alerts,
    }
    run_path = _save_run_report(report)
    return overall_ok, run_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify mesh hash-chain integrity and alert on first divergence.")
    parser.add_argument("--env-file", action="append", required=True, help="Path to mesh env file (repeatable).")
    return parser


def main() -> int:
    args = _parser().parse_args()
    env_files = [Path(item).resolve() for item in args.env_file]
    ok, run_path = run(env_files)
    print(str(run_path))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
