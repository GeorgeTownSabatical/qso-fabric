from __future__ import annotations

import argparse
import asyncio
import json
import os
import ssl
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify-hardened-wss",
        description="Verify fail-closed hardened qso-chat-ws profile.",
    )
    parser.add_argument("--env-file", default=".codex/state/qso_chat_ws.env")
    parser.add_argument("--session-token", default="submission-wss-check")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout-sec", type=float, default=12.0)
    return parser


def _load_env_file(path: Path) -> dict[str, str]:
    env_values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_values[key.strip()] = value.strip()
    return env_values


def _start_server(env: dict[str, str]) -> subprocess.Popen[str]:
    cmd = [str(ROOT / "tools" / "run_qso_chat_ws_hardened.sh")]
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _seed_message(env: dict[str, str], session_token: str) -> None:
    cmd = [
        str(ROOT / ".venv" / "bin" / "qso-chat"),
        session_token,
        "--author",
        "submission-check",
        "--role",
        "user",
        "--content",
        "submission readiness verification",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"failed to seed chat message: {proc.stderr.strip()}")


async def _verify_over_wss(env: dict[str, str], *, session_token: str, limit: int, timeout_sec: float) -> dict[str, Any]:
    import websockets

    host = env.get("QSO_CHAT_WS_HOST", "127.0.0.1").strip() or "127.0.0.1"
    if host == "0.0.0.0":
        host = "127.0.0.1"
    port = int(env.get("QSO_CHAT_WS_PORT", "9444"))
    auth = env.get("QSO_CHAT_WS_AUTH_TOKEN", "").strip()
    uri = f"wss://{host}:{port}"

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    deadline = time.monotonic() + timeout_sec
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            async with websockets.connect(uri, ssl=ssl_ctx) as ws:
                await ws.send(json.dumps({"type": "handshake", "auth_token": auth}))
                handshake = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))

                await ws.send(
                    json.dumps(
                        {
                            "type": "tail",
                            "auth_token": auth,
                            "session_token": session_token,
                            "limit": limit,
                        }
                    )
                )
                tail = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
                return {"handshake": handshake, "tail": tail}
        except Exception as exc:  # pragma: no cover - transient boot race
            last_error = str(exc)
            await asyncio.sleep(0.2)

    raise RuntimeError(f"failed WSS verification handshake within timeout: {last_error or 'unknown error'}")


def _assert_hardened_contract(payload: dict[str, Any]) -> dict[str, Any]:
    handshake = payload.get("handshake", {})
    tail = payload.get("tail", {})

    assert handshake.get("transport") == "wss", "transport must be wss"
    assert handshake.get("auth_required") is True, "auth must be required"
    assert handshake.get("quantum_envelope_enabled") is True, "quantum envelope must be enabled"
    assert handshake.get("contract_anchor_enabled") is True, "contract anchor must be enabled"
    assert handshake.get("signature_algo") == "ML-DSA-65", "signature algo mismatch"
    assert handshake.get("kem_algo") == "ML-KEM-768", "kem algo mismatch"

    security = tail.get("_qso_security", {})
    assert isinstance(security, dict), "missing _qso_security envelope"
    assert isinstance(security.get("quantum_envelope"), dict), "missing quantum envelope payload"
    assert isinstance(security.get("contract_anchor"), dict), "missing contract anchor payload"

    anchor_mode = security["contract_anchor"].get("mode")
    assert anchor_mode in {"local_deterministic", "ethereum_deterministic", "ethereum_live"}, "invalid anchor mode"

    return {
        "transport": handshake.get("transport"),
        "auth_required": handshake.get("auth_required"),
        "signature_algo": handshake.get("signature_algo"),
        "kem_algo": handshake.get("kem_algo"),
        "quantum_envelope_enabled": handshake.get("quantum_envelope_enabled"),
        "contract_anchor_enabled": handshake.get("contract_anchor_enabled"),
        "anchor_mode": anchor_mode,
        "messages_returned": len(tail.get("messages", [])),
    }


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    env_file = (ROOT / args.env_file).resolve()
    if not env_file.exists():
        raise SystemExit(f"missing env file: {env_file}")

    env_values = _load_env_file(env_file)
    env = os.environ.copy()
    env.update(env_values)
    env["PYTHONUNBUFFERED"] = "1"
    oqs_path = env.get("QSO_CHAT_WS_OQS_INSTALL_PATH", "").strip()
    if oqs_path:
        env["OQS_INSTALL_PATH"] = oqs_path

    _seed_message(env, args.session_token)
    proc = _start_server(env)
    try:
        payload = asyncio.run(
            _verify_over_wss(
                env,
                session_token=args.session_token,
                limit=max(1, int(args.limit)),
                timeout_sec=max(2.0, float(args.timeout_sec)),
            )
        )
        out = _assert_hardened_contract(payload)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

    print(json.dumps({"ok": True, "result": out}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1:])
