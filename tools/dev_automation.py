from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / ".venv" / "bin" / "python"
BOOTSTRAP_STAMP = ROOT / ".venv" / ".qso_dev_bootstrap.sha256"
DEFAULT_TESTS = [
    "tests/test_dev_automation.py",
    "tests/test_mcp_qso_edu.py",
    "tests/test_mcp_qso_edu_protocol.py",
    "tests/test_apc_bayes_compare.py",
    "tests/test_qso_edu_apc_bootstrap_cli.py",
    "tests/test_sandbox_mcp_compat.py",
    "tests/test_conversation_bridge.py",
    "tests/test_pq_keys_nist.py",
    "tests/test_qso_chat.py",
    "tests/test_plus_bridge_https.py",
]
DEFAULT_LINT_TARGETS = ["mcp_qso_edu", "tools", "tests"]
DEFAULT_PROPERTY_FRAUD_INPUT_DIR = ROOT / ".codex" / "state" / "solis_property_deeds_inbox"
DEFAULT_PROPERTY_FRAUD_INPUT = ROOT / ".codex" / "state" / "solis_property_deeds_input.jsonl"
DEFAULT_PROPERTY_FRAUD_OUTPUT = ROOT / ".codex" / "state" / "solis_property_fraud_scores.jsonl"
DEFAULT_PROPERTY_FRAUD_SUMMARY = ROOT / ".codex" / "state" / "solis_property_fraud_summary.json"
DEFAULT_PROPERTY_FRAUD_CHECKPOINT = ROOT / ".codex" / "state" / "solis_property_fraud_checkpoint.json"
DEFAULT_OC_APN_DB_PATH = ROOT / ".codex" / "state" / "orange_county_apn" / "apn_orange_county_ca.sqlite3"
DEFAULT_OC_APN_SUMMARY_PATH = ROOT / ".codex" / "state" / "orange_county_apn" / "summary.json"
DEFAULT_OC_APN_CHECKPOINT_PATH = ROOT / ".codex" / "state" / "orange_county_apn" / "checkpoint.json"
DEFAULT_OC_APN_ENDPOINT = "https://ocgis.com/arcpub/rest/services/LegalLotsAttributeOpenData/FeatureServer/0"
DEFAULT_OC_SCOPE_SUMMARY_PATH = ROOT / ".codex" / "state" / "orange_county_apn" / "scope_summary.json"
DEFAULT_OC_SCOPE_CHECKPOINT_PATH = ROOT / ".codex" / "state" / "orange_county_apn" / "history_checkpoint.json"


def _run(cmd: Sequence[str], *, cwd: Path = ROOT) -> None:
    rendered = " ".join(cmd)
    print(f"[qso-dev] {rendered}")
    proc = subprocess.run(list(cmd), cwd=str(cwd), env=os.environ.copy(), check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _env_flag(name: str) -> bool:
    raw = str(os.environ.get(name, "")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _bootstrap_fingerprint() -> str:
    digest = hashlib.sha256()
    for rel in ("pyproject.toml", "requirements.txt"):
        path = ROOT / rel
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _ensure_venv() -> None:
    if not VENV_PY.exists():
        _run(["python3", "-m", "venv", ".venv"])
    if os.environ.get("QSO_DEV_FORCE_INSTALL") == "1":
        _run([str(VENV_PY), "-m", "pip", "install", "-e", ".[dev]"])
        BOOTSTRAP_STAMP.write_text(_bootstrap_fingerprint(), encoding="utf-8")
        return
    fingerprint = _bootstrap_fingerprint()
    if BOOTSTRAP_STAMP.exists() and BOOTSTRAP_STAMP.read_text(encoding="utf-8").strip() == fingerprint:
        print("[qso-dev] bootstrap cache hit; skipping dependency reinstall")
        return
    _run([str(VENV_PY), "-m", "pip", "install", "-e", ".[dev]"])
    BOOTSTRAP_STAMP.write_text(fingerprint, encoding="utf-8")


def _lint() -> None:
    _run([str(VENV_PY), "-m", "ruff", "check", *DEFAULT_LINT_TARGETS])


def _tests() -> None:
    _run([str(VENV_PY), "-m", "pytest", "-q", *DEFAULT_TESTS])


def _smoke() -> None:
    _run([str(VENV_PY), "tools/smoke_chat_stack.py"])


def _property_fraud() -> None:
    input_dir = Path(os.environ.get("QSO_DEV_PROPERTY_FRAUD_INPUT_DIR", str(DEFAULT_PROPERTY_FRAUD_INPUT_DIR)))
    input_path = Path(os.environ.get("QSO_DEV_PROPERTY_FRAUD_INPUT", str(DEFAULT_PROPERTY_FRAUD_INPUT)))
    output_path = Path(os.environ.get("QSO_DEV_PROPERTY_FRAUD_OUTPUT", str(DEFAULT_PROPERTY_FRAUD_OUTPUT)))
    summary_path = Path(os.environ.get("QSO_DEV_PROPERTY_FRAUD_SUMMARY", str(DEFAULT_PROPERTY_FRAUD_SUMMARY)))
    checkpoint_path = Path(os.environ.get("QSO_DEV_PROPERTY_FRAUD_CHECKPOINT", str(DEFAULT_PROPERTY_FRAUD_CHECKPOINT)))

    input_dir_has_files = False
    if input_dir.exists():
        for pattern in ("*.json", "*.jsonl"):
            if any(input_dir.rglob(pattern)):
                input_dir_has_files = True
                break

    if input_dir_has_files:
        cmd = [
            str(VENV_PY),
            "-m",
            "tools.solis_property_fraud",
            "batch",
            "--input-dir",
            str(input_dir),
            "--recursive",
            "--output",
            str(output_path),
            "--summary",
            str(summary_path),
            "--checkpoint",
            str(checkpoint_path),
        ]
        if _env_flag("QSO_DEV_PROPERTY_FRAUD_RESET_CHECKPOINT"):
            cmd.append("--reset-checkpoint")
        if _env_flag("QSO_DEV_PROPERTY_FRAUD_REPLACE_OUTPUT"):
            cmd.append("--replace-output")
        _run(cmd)
        return

    if input_path.exists():
        _run(
            [
                str(VENV_PY),
                "-m",
                "tools.solis_property_fraud",
                "run",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--summary",
                str(summary_path),
            ]
        )
        return

    _run(
        [
            str(VENV_PY),
            "-m",
            "tools.solis_property_fraud",
            "demo",
            "--output",
            str(output_path),
            "--summary",
            str(summary_path),
        ]
    )


def _orange_county_apn_db() -> None:
    db_path = Path(os.environ.get("QSO_DEV_OC_APN_DB_PATH", str(DEFAULT_OC_APN_DB_PATH)))
    summary_path = Path(os.environ.get("QSO_DEV_OC_APN_SUMMARY_PATH", str(DEFAULT_OC_APN_SUMMARY_PATH)))
    checkpoint_path = Path(os.environ.get("QSO_DEV_OC_APN_CHECKPOINT_PATH", str(DEFAULT_OC_APN_CHECKPOINT_PATH)))
    endpoint = os.environ.get("QSO_DEV_OC_APN_ENDPOINT", DEFAULT_OC_APN_ENDPOINT)

    cmd = [
        str(VENV_PY),
        "-m",
        "tools.solis_orange_county_apn_db",
        "sync",
        "--endpoint",
        endpoint,
        "--db",
        str(db_path),
        "--summary",
        str(summary_path),
        "--checkpoint",
        str(checkpoint_path),
    ]

    batch_size = str(os.environ.get("QSO_DEV_OC_APN_BATCH_SIZE", "")).strip()
    if batch_size:
        cmd.extend(["--batch-size", batch_size])

    max_batches = str(os.environ.get("QSO_DEV_OC_APN_MAX_BATCHES", "")).strip()
    if max_batches:
        cmd.extend(["--max-batches", max_batches])

    if _env_flag("QSO_DEV_OC_APN_RESET_CHECKPOINT"):
        cmd.append("--reset-checkpoint")
    if _env_flag("QSO_DEV_OC_APN_FULL_REFRESH"):
        cmd.append("--full-refresh")

    _run(cmd)


def _orange_county_scope() -> None:
    db_path = Path(os.environ.get("QSO_DEV_OC_APN_DB_PATH", str(DEFAULT_OC_APN_DB_PATH)))
    summary_path = Path(os.environ.get("QSO_DEV_OC_SCOPE_SUMMARY_PATH", str(DEFAULT_OC_SCOPE_SUMMARY_PATH)))
    checkpoint_path = Path(os.environ.get("QSO_DEV_OC_SCOPE_CHECKPOINT_PATH", str(DEFAULT_OC_SCOPE_CHECKPOINT_PATH)))

    cmd = [
        str(VENV_PY),
        "-m",
        "tools.solis_orange_county_scope",
        "run-all",
        "--db",
        str(db_path),
        "--summary",
        str(summary_path),
        "--checkpoint",
        str(checkpoint_path),
    ]

    batch_size = str(os.environ.get("QSO_DEV_OC_SCOPE_BATCH_SIZE", "")).strip()
    if batch_size:
        cmd.extend(["--batch-size", batch_size])

    max_batches = str(os.environ.get("QSO_DEV_OC_SCOPE_MAX_BATCHES_PER_SOURCE", "")).strip()
    if max_batches:
        cmd.extend(["--max-batches-per-source", max_batches])

    if _env_flag("QSO_DEV_OC_SCOPE_RESET_CHECKPOINT"):
        cmd.append("--reset-checkpoint")

    _run(cmd)


def _submission() -> None:
    _run([str(VENV_PY), "tools/prepare_submission_bundle.py"])


def _install_hook() -> None:
    git_hooks = ROOT / ".git" / "hooks"
    if not git_hooks.exists():
        raise SystemExit("[qso-dev] .git/hooks not found; run inside a git worktree")
    hook_path = git_hooks / "pre-commit"
    script = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'ROOT="$(git rev-parse --show-toplevel)"\n'
        'if [ -x "$ROOT/.venv/bin/python" ]; then\n'
        '  "$ROOT/.venv/bin/python" "$ROOT/tools/dev_automation.py" quick\n'
        "else\n"
        '  python3 "$ROOT/tools/dev_automation.py" quick\n'
        "fi\n"
    )
    hook_path.write_text(script, encoding="utf-8")
    hook_path.chmod(0o755)
    print(f"[qso-dev] installed pre-commit hook at {hook_path}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qso-dev", description="Automate local development workflows")
    parser.add_argument(
        "command",
        choices=[
            "bootstrap",
            "lint",
            "test",
            "quick",
            "smoke",
            "all",
            "hook-install",
            "ci",
            "property-fraud",
            "apn-db",
            "apn-scope",
            "submission",
        ],
    )
    return parser


def run(command: str) -> None:
    if command == "bootstrap":
        _ensure_venv()
        return
    if command == "lint":
        _ensure_venv()
        _lint()
        return
    if command == "test":
        _ensure_venv()
        _tests()
        return
    if command == "quick":
        _ensure_venv()
        _lint()
        _tests()
        return
    if command == "smoke":
        _ensure_venv()
        _smoke()
        return
    if command in {"all", "ci"}:
        _ensure_venv()
        _lint()
        _tests()
        _smoke()
        return
    if command == "property-fraud":
        _ensure_venv()
        _property_fraud()
        return
    if command == "apn-db":
        _ensure_venv()
        _orange_county_apn_db()
        return
    if command == "apn-scope":
        _ensure_venv()
        _orange_county_scope()
        return
    if command == "submission":
        _ensure_venv()
        _submission()
        return
    if command == "hook-install":
        _install_hook()
        return
    raise SystemExit(f"unsupported command: {command}")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    run(args.command)


if __name__ == "__main__":
    main(sys.argv[1:])
