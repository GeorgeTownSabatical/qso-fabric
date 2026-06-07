from __future__ import annotations

import json
import subprocess
from contextlib import suppress
from dataclasses import dataclass
from itertools import count
from typing import Any


class UpstreamMCPError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class UpstreamAppConfig:
    name: str
    command: tuple[str, ...]


class UpstreamMCPClient:
    """Thin JSON-RPC stdio client for an upstream MCP server process."""

    def __init__(self, config: UpstreamAppConfig) -> None:
        self.config = config
        self._proc: subprocess.Popen[str] | None = None
        self._ids = count(1)

    def list_tools(self) -> list[dict[str, Any]]:
        self._initialize()
        response = self._request("tools/list", {})
        tools = response.get("tools", [])
        if not isinstance(tools, list):
            raise UpstreamMCPError("upstream tools/list returned invalid payload")
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        self._initialize()
        response = self._request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments or {},
            },
        )
        if not isinstance(response, dict):
            raise UpstreamMCPError("upstream tools/call returned invalid payload")
        return response

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        if proc.stdin is not None:
            with suppress(Exception):
                request = {"jsonrpc": "2.0", "id": 0, "method": "exit", "params": {}}
                proc.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
                proc.stdin.flush()
        proc.terminate()
        with suppress(Exception):
            proc.wait(timeout=1)
        if proc.poll() is None:
            proc.kill()
            with suppress(Exception):
                proc.wait(timeout=1)

    def _initialize(self) -> None:
        self._ensure_started()
        self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "qso-edu-mcp", "version": "0.1.0"},
            },
        )

    def _ensure_started(self) -> None:
        if self._proc is not None:
            return
        self._proc = subprocess.Popen(
            list(self.config.command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_started()
        assert self._proc is not None
        if self._proc.stdin is None or self._proc.stdout is None:
            raise UpstreamMCPError(f"upstream app '{self.config.name}' stdio not available")

        request_id = next(self._ids)
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        self._proc.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self._proc.stdin.flush()

        while True:
            line = self._proc.stdout.readline()
            if line == "":
                raise UpstreamMCPError(f"upstream app '{self.config.name}' closed the stream")

            payload = json.loads(line)
            if payload.get("id") != request_id:
                continue

            if "error" in payload:
                error = payload["error"]
                message = error.get("message") if isinstance(error, dict) else str(error)
                raise UpstreamMCPError(f"upstream app '{self.config.name}' error: {message}")

            result = payload.get("result")
            if not isinstance(result, dict):
                raise UpstreamMCPError(f"upstream app '{self.config.name}' response missing result object")
            return result


class UpstreamAppBridge:
    """Registry and lifecycle management for upstream MCP app connections."""

    ENV_VAR = "QSO_EDU_UPSTREAM_APPS"

    def __init__(self, configs: dict[str, UpstreamAppConfig] | None = None) -> None:
        self._configs = configs or {}
        self._clients: dict[str, UpstreamMCPClient] = {}

    @classmethod
    def from_env(cls) -> "UpstreamAppBridge":
        import os

        raw = os.getenv(cls.ENV_VAR, "").strip()
        if not raw:
            return cls()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError(f"{cls.ENV_VAR} must be a JSON object")

        configs: dict[str, UpstreamAppConfig] = {}
        for name, command in payload.items():
            if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
                raise ValueError(f"{cls.ENV_VAR}.{name} must be a non-empty string array command")
            configs[str(name)] = UpstreamAppConfig(name=str(name), command=tuple(command))
        return cls(configs)

    def has_apps(self) -> bool:
        return bool(self._configs)

    def list_apps(self) -> list[dict[str, Any]]:
        return [{"name": config.name, "command": list(config.command)} for config in self._configs.values()]

    def list_tools(self, app: str) -> list[dict[str, Any]]:
        return self._client(app).list_tools()

    def call_tool(self, app: str, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._client(app).call_tool(name, arguments)

    def close(self) -> None:
        for client in self._clients.values():
            client.close()
        self._clients.clear()

    def _client(self, app: str) -> UpstreamMCPClient:
        normalized = str(app).strip()
        if normalized not in self._configs:
            raise KeyError(f"unknown upstream app: {normalized}")
        client = self._clients.get(normalized)
        if client is None:
            client = UpstreamMCPClient(self._configs[normalized])
            self._clients[normalized] = client
        return client
