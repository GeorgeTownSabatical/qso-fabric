from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True, check=False)


def _start(cmd: list[str], env: dict[str, str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _wait_port(host: str, port: int, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.5)
            try:
                sock.connect((host, port))
                return True
            except OSError:
                time.sleep(0.1)
    return False


def _jsonrpc(proc: subprocess.Popen[str], method: str, params: dict | None = None, rid: int = 1) -> dict:
    assert proc.stdin is not None
    assert proc.stdout is not None
    req = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError(f"no response for {method}")
    payload = json.loads(line)
    if "error" in payload:
        raise RuntimeError(f"jsonrpc error: {payload['error']}")
    return payload["result"]


def _stop(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        if proc.stdin is not None:
            try:
                proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 999, "method": "exit", "params": {}}) + "\n")
                proc.stdin.flush()
            except Exception:
                pass
        proc.terminate()
        proc.wait(timeout=2)
    except Exception:
        proc.kill()


def main() -> None:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    # Keep the virtualenv shim directory, not the resolved framework path.
    venv_bin = str(Path(sys.executable).parent)
    env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
    session_token = "ci-smoke-session"
    results: list[dict[str, object]] = []

    # qso-chat CLI manual path
    append = _run(["qso-chat", session_token, "--author", "ci", "--role", "user", "--content", "smoke"], env)
    if append.returncode != 0:
        raise RuntimeError(f"qso-chat append failed: {append.stderr}")
    appended = json.loads(append.stdout)
    results.append({"check": "qso-chat append", "message_id": appended["message"]["id"]})

    tail = _run(["qso-chat", session_token, "--tail", "5"], env)
    if tail.returncode != 0:
        raise RuntimeError(f"qso-chat tail failed: {tail.stderr}")
    tailed = json.loads(tail.stdout)
    results.append({"check": "qso-chat tail", "messages": len(tailed["messages"])})

    # stdio MCP path
    proc = _start(["qso-edu-mcp-stdio"], env)
    try:
        _jsonrpc(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "1"}}, rid=1)
        sandbox = _jsonrpc(proc, "tools/call", {"name": "qso.create_sandbox", "arguments": {"session_token": "ci-stdio"}}, rid=2)
        sandbox_id = sandbox["content"][0]["json"]["sandbox_id"]
        _jsonrpc(proc, "tools/call", {"name": "qso.chat.init", "arguments": {"sandbox_id": sandbox_id}}, rid=3)
        _jsonrpc(proc, "tools/call", {"name": "qso.chat.append", "arguments": {"sandbox_id": sandbox_id, "author": "ci", "role": "user", "content": "hello"}}, rid=4)
        verify = _jsonrpc(proc, "tools/call", {"name": "qso.chat.verify", "arguments": {"sandbox_id": sandbox_id, "strict": True}}, rid=5)
        failed = verify["content"][0]["json"]["result"]["audit"]["failed_messages"]
        if failed != 0:
            raise RuntimeError(f"signature verify failed: {failed}")
        results.append({"check": "stdio mcp chat+verify", "failed_messages": failed})
    finally:
        _stop(proc)

    # Upstream app bridge via llm template
    up_env = dict(env)
    up_env["QSO_EDU_UPSTREAM_APPS"] = json.dumps({"llm": ["python3", "tools/llm_mcp_server.py"]})
    proc = _start(["qso-edu-mcp-stdio", "--enable-upstream-apps"], up_env)
    try:
        _jsonrpc(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "1"}}, rid=10)
        called = _jsonrpc(
            proc,
            "tools/call",
            {
                "name": "mcp.apps.call",
                "arguments": {
                    "app": "llm",
                    "tool": "llm.respond",
                    "arguments": {"messages": [{"role": "user", "content": "smoke"}]},
                },
            },
            rid=11,
        )
        payload = called["content"][0]["json"]["result"]["content"][0]["json"]
        if not isinstance(payload, dict) or "ok" not in payload:
            raise RuntimeError("invalid llm bridge payload")
        results.append({"check": "upstream llm bridge", "ok": payload.get("ok", False)})
    finally:
        _stop(proc)

    # HTTP relay
    bridge_path = ROOT / ".codex/state/plus_bridge_smoke_ci.jsonl"
    http_proc = subprocess.Popen(
        ["qso-plus-bridge-http", "--host", "127.0.0.1", "--port", "8875", "--path", str(bridge_path)],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        if not _wait_port("127.0.0.1", 8875, 5):
            raise RuntimeError("http bridge did not start")
        req = Request(
            "http://127.0.0.1:8875/bridge/append",
            data=json.dumps({"source": "ci", "content": "relay"}).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=5) as resp:
            appended_payload = json.loads(resp.read().decode("utf-8"))
        if int(appended_payload.get("seq", 0)) <= 0:
            raise RuntimeError("bridge append failed")
        results.append({"check": "http relay", "seq": appended_payload["seq"]})
    finally:
        if http_proc.poll() is None:
            http_proc.terminate()
            try:
                http_proc.wait(timeout=2)
            except Exception:
                http_proc.kill()

    # websocket read-only tail viewer
    ws_proc = subprocess.Popen(
        ["qso-chat-ws", "--host", "127.0.0.1", "--port", "8876"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        if not _wait_port("127.0.0.1", 8876, 5):
            raise RuntimeError("ws viewer did not start")

        async def _ws_check() -> int:
            import websockets

            async with websockets.connect("ws://127.0.0.1:8876") as ws:
                await ws.send(json.dumps({"type": "tail", "session_token": session_token, "limit": 5}))
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                payload = json.loads(raw)
                return len(payload.get("messages", []))

        count = asyncio.run(_ws_check())
        results.append({"check": "ws viewer", "messages": count})
    finally:
        if ws_proc.poll() is None:
            ws_proc.terminate()
            try:
                ws_proc.wait(timeout=2)
            except Exception:
                ws_proc.kill()

    print(json.dumps({"ok": True, "results": results}, indent=2))


if __name__ == "__main__":
    main()
