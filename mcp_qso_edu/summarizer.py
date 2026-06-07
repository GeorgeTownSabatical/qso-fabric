from __future__ import annotations

from typing import Any

MAX_MESSAGES = 40


def summarize(messages: list[dict[str, Any]]) -> str:
    """Deterministic, LLM-free fallback summarizer."""
    key_points: list[str] = []
    for message in messages[-MAX_MESSAGES:]:
        role = str(message.get("role", ""))
        if role in {"user", "assistant"}:
            content = str(message.get("content", "")).strip()
            if content:
                key_points.append(f"{role}: {content[:120]}")
    return " | ".join(key_points)
