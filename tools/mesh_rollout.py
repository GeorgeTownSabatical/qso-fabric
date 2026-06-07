from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".codex" / "state" / "mesh_rollout"

ROLLOUT_FILES = [
    "services/runtime.py",
    "storage/event_store/__init__.py",
    "services/transport/audit_logger.py",
    "services/transport/state_store.py",
    "mcp_qso_edu/conversation_bridge.py",
    "mcp_qso_edu/sandbox_persistence.py",
    "solis/shared/file_lock.py",
    "docs/mesh_handoff_contract.md",
    "tools/mesh_rollout.py",
    "tools/mesh_configure_env.py",
    "tools/mesh_dual_writer_smoke.py",
    "tools/mesh_integrity_check.py",
    "tools/run_mesh_integrity_scheduled.sh",
    "tools/setup_mesh_integrity_cron.sh",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _utc_ts_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _copy_file(source_root: Path, target_root: Path, rel: str) -> dict[str, str]:
    src = source_root / rel
    dst = target_root / rel
    if not src.exists():
        return {"status": "missing_source", "path": rel}

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    src_hash = _sha256(src)
    dst_hash = _sha256(dst)
    status = "ok" if src_hash == dst_hash else "hash_mismatch"
    return {"status": status, "path": rel, "source_hash": src_hash, "target_hash": dst_hash}


def run(source_root: Path, targets: list[Path]) -> Path:
    run_id = _utc_ts_compact()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    report_path = STATE_DIR / f"rollout_{run_id}.json"

    report: dict[str, object] = {
        "run_id": run_id,
        "source_root": str(source_root),
        "targets": [],
    }

    target_rows: list[dict[str, object]] = []
    for target in targets:
        target_result: dict[str, object] = {
            "target_root": str(target),
            "results": [],
            "ok": True,
        }
        file_results: list[dict[str, str]] = []
        for rel in ROLLOUT_FILES:
            row = _copy_file(source_root, target, rel)
            file_results.append(row)
            if row.get("status") != "ok":
                target_result["ok"] = False
        target_result["results"] = file_results
        target_rows.append(target_result)

    report["targets"] = target_rows
    report["ok"] = all(bool(row.get("ok")) for row in target_rows)
    report["created_at"] = datetime.now(timezone.utc).isoformat()
    report_path.write_text(json.dumps(report, sort_keys=True, indent=2), encoding="utf-8")
    return report_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Roll out mesh-critical files to target instances.")
    parser.add_argument("--source-root", default=str(ROOT))
    parser.add_argument("--target", action="append", required=True, help="Target instance root (repeatable).")
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    source_root = Path(args.source_root).resolve()
    targets = [Path(item).resolve() for item in args.target]
    report_path = run(source_root, targets)
    print(str(report_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
