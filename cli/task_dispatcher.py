from __future__ import annotations

from mapl.executor import run
from router.context_router import route
from .codex_bridge import CodexBridge


def dispatch(command: str) -> dict[str, object]:
    parsed = run(command)
    plan = route(parsed["context"], parsed["modules"])
    bridge = CodexBridge()
    return bridge.dispatch({"parsed": parsed, "plan": plan})
