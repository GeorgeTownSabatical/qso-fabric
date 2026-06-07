from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


CONVERSATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["messages"],
    "properties": {
        "messages": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "author", "role", "content", "timestamp"],
                "properties": {
                    "id": {"type": "string"},
                    "author": {"type": "string"},
                    "role": {"type": "string", "enum": ["user", "assistant", "agent", "system"]},
                    "content": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "meta": {"type": "object"},
                },
            },
        }
    },
}


def conversation_uri(sandbox_id: str, conversation_id: str = "main") -> str:
    normalized = str(conversation_id).strip() or "main"
    return f"qso://sandbox/{sandbox_id}/conversation/{normalized}"


def init_conversation(app, sandbox_id: str, conversation_id: str = "main") -> dict[str, Any]:
    out = app.qso_chat_init(sandbox_id, conversation_id=conversation_id)
    payload = out.get("result", {})
    return {
        "uri": payload.get("uri", conversation_uri(sandbox_id, conversation_id)),
        "created": bool(payload.get("created", False)),
        "qso": payload.get("qso", {}),
    }


def append_message(
    app,
    sandbox_id: str,
    author: str,
    role: str,
    content: str,
    meta: dict[str, Any] | None = None,
    conversation_id: str = "main",
) -> dict[str, Any]:
    out = app.qso_chat_append(
        sandbox_id,
        conversation_id=conversation_id,
        author=str(author),
        role=str(role),
        content=str(content),
        actor=str(author),
        metadata=meta or {},
    )
    payload = out.get("result", {})
    message = payload.get("message", {})
    if isinstance(message, dict) and message:
        return message
    # Fallback shape if upstream implementation changes.
    return {
        "id": str(uuid4()),
        "author": str(author),
        "role": str(role),
        "content": str(content),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": meta or {},
    }


def tail_messages(app, sandbox_id: str, limit: int = 20, conversation_id: str = "main") -> dict[str, Any]:
    out = app.qso_chat_tail(sandbox_id, conversation_id=conversation_id, limit=limit)
    payload = out.get("result", {})
    return {
        "uri": payload.get("uri", conversation_uri(sandbox_id, conversation_id)),
        "messages": payload.get("messages", []),
    }
