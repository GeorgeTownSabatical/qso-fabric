from __future__ import annotations

import json
import os
import sys
import time
from collections import deque
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
OPENAI_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
OPENAI_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
MAX_RPM = int(os.getenv("LLM_MAX_RPM", "60"))

_WINDOW_SECONDS = 60.0
_REQUEST_TIMESTAMPS: deque[float] = deque()


def _ok(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, **payload}


def _error(code: str, message: str, *, retriable: bool = False) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "retriable": bool(retriable),
        },
    }


def _fake_llm(messages: list[dict[str, Any]]) -> dict[str, Any]:
    if not messages:
        return _ok({"mode": "fallback", "text": "[model] No context provided."})
    last = str(messages[-1].get("content", ""))
    return _ok({"mode": "fallback", "text": f"[model] Acknowledged: {last[:200]}"})


def _enforce_rate_limit() -> None:
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS
    while _REQUEST_TIMESTAMPS and _REQUEST_TIMESTAMPS[0] < cutoff:
        _REQUEST_TIMESTAMPS.popleft()
    if len(_REQUEST_TIMESTAMPS) >= MAX_RPM:
        raise RuntimeError("rate limit exceeded")
    _REQUEST_TIMESTAMPS.append(now)


def _coerce_messages(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "user")).strip() or "user"
        content = str(item.get("content", "")).strip()
        out.append({"role": role, "content": content})
    return out


def _call_openai(messages: list[dict[str, str]], *, model: str, temperature: float) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        return _fake_llm(messages)

    body = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature),
    }
    payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    last_error: dict[str, Any] | None = None
    for attempt in range(OPENAI_MAX_RETRIES + 1):
        try:
            request = Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers=headers,
                method="POST",
            )
            with urlopen(request, timeout=OPENAI_TIMEOUT_SECONDS) as response:
                raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
            choices = parsed.get("choices", [])
            if not isinstance(choices, list) or not choices:
                return _error("invalid_response", "No choices returned by provider")
            first = choices[0] if isinstance(choices[0], dict) else {}
            message = first.get("message", {}) if isinstance(first, dict) else {}
            text = str(message.get("content", ""))
            return _ok({"mode": "openai", "text": text, "model": model})
        except HTTPError as exc:
            retriable = exc.code >= 500 or exc.code == 429
            last_error = _error("http_error", f"{exc.code} {exc.reason}", retriable=retriable)
            if retriable and attempt < OPENAI_MAX_RETRIES:
                time.sleep(0.25 * (attempt + 1))
                continue
            return last_error
        except URLError as exc:
            last_error = _error("network_error", str(exc.reason), retriable=True)
            if attempt < OPENAI_MAX_RETRIES:
                time.sleep(0.25 * (attempt + 1))
                continue
            return last_error
        except TimeoutError:
            last_error = _error("timeout", "Provider request timed out", retriable=True)
            if attempt < OPENAI_MAX_RETRIES:
                time.sleep(0.25 * (attempt + 1))
                continue
            return last_error
        except Exception as exc:  # pragma: no cover - defensive fallback
            return _error("unexpected_error", str(exc))
    return last_error or _error("unknown_error", "Unknown provider failure")


def _tool_list() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": "llm.respond",
                "description": "Generate a model response from chat messages.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "messages": {"type": "array"},
                        "model": {"type": "string"},
                        "temperature": {"type": "number"},
                    },
                },
            }
        ]
    }


def _tool_call(params: dict[str, Any]) -> dict[str, Any]:
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        return {"content": [{"type": "json", "json": _error("invalid_arguments", "arguments must be an object")}]}

    messages = _coerce_messages(arguments.get("messages", []))
    if not messages:
        return {"content": [{"type": "json", "json": _error("invalid_messages", "messages must be a non-empty list")}]}

    model = str(arguments.get("model", OPENAI_MODEL)).strip() or OPENAI_MODEL
    temperature = float(arguments.get("temperature", 0.2))

    try:
        _enforce_rate_limit()
    except RuntimeError:
        result = _error("rate_limited", "Local MCP rate limit exceeded", retriable=True)
        return {"content": [{"type": "json", "json": result}]}

    result = _call_openai(messages, model=model, temperature=temperature)
    return {"content": [{"type": "json", "json": result}]}


def main() -> None:
    for line in sys.stdin:
        request = json.loads(line)
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        if not isinstance(params, dict):
            params = {}

        if method == "initialize":
            result = {"serverInfo": {"name": "llm-mcp", "version": "0.2.0"}}
        elif method == "tools/list":
            result = _tool_list()
        elif method == "tools/call":
            result = _tool_call(params)
        elif method in {"shutdown", "exit"}:
            result = {"ok": True}
        else:
            result = _error("unknown_method", f"unknown method {method}")

        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}) + "\n")
        sys.stdout.flush()

        if method in {"shutdown", "exit"}:
            break


if __name__ == "__main__":
    main()
