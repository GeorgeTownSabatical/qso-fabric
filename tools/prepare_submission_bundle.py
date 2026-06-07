from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CommandSpec:
    name: str
    cmd: list[str]
    env_overrides: dict[str, str]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha384_file(path: Path) -> str:
    digest = hashlib.sha384()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prepare-submission-bundle",
        description="Create a reproducible submission-readiness evidence bundle.",
    )
    parser.add_argument(
        "--output-root",
        default=".codex/state/submissions",
        help="Directory where bundles are created.",
    )
    parser.add_argument(
        "--oqs-install-path",
        default="",
        help="liboqs install root (contains lib/liboqs*). Defaults to env or hardened ws env file.",
    )
    parser.add_argument(
        "--env-file",
        default=".codex/state/qso_chat_ws.env",
        help="Hardened WS env file used for live verification.",
    )
    return parser


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _resolve_oqs_path(cli_value: str, file_values: dict[str, str], env: dict[str, str]) -> str:
    for candidate in (
        cli_value.strip(),
        env.get("OQS_INSTALL_PATH", "").strip(),
        env.get("QSO_PQ_OQS_INSTALL_PATH", "").strip(),
        env.get("QSO_CHAT_WS_OQS_INSTALL_PATH", "").strip(),
        file_values.get("QSO_CHAT_WS_OQS_INSTALL_PATH", "").strip(),
    ):
        if candidate:
            return candidate
    return ""


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_command(
    spec: CommandSpec,
    *,
    logs_dir: Path,
    base_env: dict[str, str],
) -> dict[str, Any]:
    env = base_env.copy()
    env.update(spec.env_overrides)
    started_at = _now()
    start = time.monotonic()
    proc = subprocess.run(
        spec.cmd,
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    duration_ms = int((time.monotonic() - start) * 1000)
    ended_at = _now()

    stdout_path = logs_dir / f"{spec.name}.stdout.log"
    stderr_path = logs_dir / f"{spec.name}.stderr.log"
    _write_text(stdout_path, proc.stdout)
    _write_text(stderr_path, proc.stderr)

    return {
        "name": spec.name,
        "cmd": spec.cmd,
        "returncode": proc.returncode,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_ms": duration_ms,
        "stdout_log": str(stdout_path.relative_to(ROOT)),
        "stderr_log": str(stderr_path.relative_to(ROOT)),
    }


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    run_id = _run_id()
    output_root = (ROOT / args.output_root).resolve()
    bundle_dir = output_root / run_id
    logs_dir = bundle_dir / "logs"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    env_file = (ROOT / args.env_file).resolve()
    file_env = _load_env_file(env_file)
    base_env = os.environ.copy()
    base_env["PYTHONUNBUFFERED"] = "1"
    oqs_path = _resolve_oqs_path(str(args.oqs_install_path), file_env, base_env)
    if not oqs_path:
        raise SystemExit("missing liboqs path; set --oqs-install-path or OQS_INSTALL_PATH/QSO_CHAT_WS_OQS_INSTALL_PATH")
    base_env["OQS_INSTALL_PATH"] = oqs_path

    clear_ws_env = {
        "QSO_CHAT_WS_HOST": "",
        "QSO_CHAT_WS_PORT": "",
        "QSO_CHAT_WS_TLS_CERT": "",
        "QSO_CHAT_WS_TLS_KEY": "",
        "QSO_CHAT_WS_AUTH_TOKEN": "",
        "QSO_CHAT_WS_PQ_SEED_HEX": "",
        "QSO_CHAT_WS_PQ_PRIVATE_KEY": "",
        "QSO_CHAT_WS_PQ_SIGNATURE_ALGO": "ML-DSA-65",
        "QSO_CHAT_WS_PQ_KEM_ALGO": "ML-KEM-768",
        "QSO_CHAT_WS_PQ_CRYPTO_PROFILE_ID": "X25519+ML-KEM-768/ML-DSA-65",
        "QSO_CHAT_WS_ANCHOR_CONTRACT_ADDRESS": "",
        "QSO_CHAT_WS_ANCHOR_RPC_URL": "",
        "QSO_CHAT_WS_ANCHOR_PRIVATE_KEY": "",
        "QSO_CHAT_WS_ANCHOR_LIVE": "0",
        "QSO_CHAT_WS_REQUIRE_TLS": "0",
        "QSO_CHAT_WS_REQUIRE_AUTH": "0",
        "QSO_CHAT_WS_REQUIRE_QUANTUM_ENVELOPE": "0",
        "QSO_CHAT_WS_REQUIRE_CONTRACT_ANCHOR": "0",
    }

    command_specs = [
        CommandSpec(name="dev_quick", cmd=["python3", "tools/dev_automation.py", "quick"], env_overrides=clear_ws_env),
        CommandSpec(name="dev_smoke", cmd=["python3", "tools/dev_automation.py", "smoke"], env_overrides=clear_ws_env),
        CommandSpec(
            name="security_tests",
            cmd=[
                str(ROOT / ".venv" / "bin" / "python"),
                "-m",
                "pytest",
                "-q",
                "tests/test_pq_keys_nist.py",
                "tests/test_quantum_socket_hardening.py",
                "tests/test_qso_chat_ws_security.py",
                "tests/test_plus_bridge_https.py",
                "tests/test_anchor_adapters.py",
            ],
            env_overrides=clear_ws_env,
        ),
        CommandSpec(
            name="verify_hardened_wss",
            cmd=[str(ROOT / ".venv" / "bin" / "python"), "tools/verify_hardened_wss.py"],
            env_overrides={**file_env, "OQS_INSTALL_PATH": oqs_path},
        ),
    ]

    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for spec in command_specs:
        result = _run_command(spec, logs_dir=logs_dir, base_env=base_env)
        results.append(result)
        if result["returncode"] != 0:
            failures.append(spec.name)

    hashed_files = [
        Path("tools/qso_chat_ws.py"),
        Path("solis/hardening/quantum_socket.py"),
        Path("solis/identity/pq_keys.py"),
        Path("tools/qso_plus_bridge_http.py"),
        Path("tools/run_qso_chat_ws_hardened.sh"),
        Path("tools/setup_qso_chat_ws_hardened.sh"),
        Path("docs/soc2_bridge_controls.md"),
        Path("docs/soc2_socket_controls.md"),
        Path("docs/submission_readiness.md"),
        Path("README.md"),
    ]
    file_hashes = []
    for rel in hashed_files:
        abs_path = ROOT / rel
        if abs_path.exists():
            file_hashes.append(
                {
                    "path": str(rel),
                    "sha384": _sha384_file(abs_path),
                }
            )

    manifest = {
        "schema_version": "1.0",
        "created_at": _now(),
        "run_id": run_id,
        "workspace_root": str(ROOT),
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "oqs_install_path": oqs_path,
            "env_file": str(env_file) if env_file.exists() else None,
        },
        "commands": results,
        "file_hashes_sha384": file_hashes,
    }
    manifest_path = bundle_dir / "manifest.json"
    _write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True))

    summary_lines = [
        f"# Submission Bundle {run_id}",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Created: `{manifest['created_at']}`",
        f"- OQS path: `{oqs_path}`",
        "",
        "## Commands",
    ]
    for result in results:
        summary_lines.append(
            f"- `{result['name']}` rc={result['returncode']} duration_ms={result['duration_ms']} "
            f"stdout=`{result['stdout_log']}` stderr=`{result['stderr_log']}`"
        )
    if failures:
        summary_lines.extend(["", "## Failures"])
        for name in failures:
            summary_lines.append(f"- `{name}`")
    summary_path = bundle_dir / "summary.md"
    _write_text(summary_path, "\n".join(summary_lines) + "\n")

    print(json.dumps({"ok": not failures, "bundle_dir": str(bundle_dir), "manifest": str(manifest_path)}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
