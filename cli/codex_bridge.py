from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexBridge:
    name: str = "codex-bridge"

    def dispatch(self, payload: dict[str, object]) -> dict[str, object]:
        return {"status": "queued", "payload": payload}
