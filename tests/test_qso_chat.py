from __future__ import annotations

from pathlib import Path

import pytest

from mcp_qso_edu.conversation_bridge import ConversationBridge
from mcp_qso_edu.crypto import verify
from mcp_qso_edu.protocol_server import QSOEduMCPProtocolServer


def _server(tmp_path: Path) -> QSOEduMCPProtocolServer:
    return QSOEduMCPProtocolServer(
        conversation_bridge=ConversationBridge(tmp_path / "bridge.jsonl"),
        state_root=tmp_path / "sandboxes",
    )


def test_chat_init_append_tail_roundtrip(tmp_path: Path) -> None:
    server = _server(tmp_path)
    sandbox_id = server.call_tool("qso.create_sandbox", {"session_token": "chat-roundtrip"})["sandbox_id"]

    init = server.call_tool("qso.chat.init", {"sandbox_id": sandbox_id})
    assert init["uri"].endswith("/conversation/main")

    append = server.call_tool(
        "qso.chat.append",
        {
            "sandbox_id": sandbox_id,
            "author": "jacob",
            "role": "user",
            "content": "hello world",
        },
    )
    message = append["message"]
    assert message["content"] == "hello world"
    assert "proof" in message
    assert verify({k: v for k, v in message.items() if k != "proof"}, message["proof"])

    tail = server.call_tool("qso.chat.tail", {"sandbox_id": sandbox_id, "limit": 10})
    assert len(tail["messages"]) == 1
    assert tail["messages"][0]["author"] == "jacob"


def test_chat_permissions_enforced(tmp_path: Path) -> None:
    server = _server(tmp_path)
    sandbox_id = server.call_tool("qso.create_sandbox", {"session_token": "chat-perms"})["sandbox_id"]
    server.call_tool("qso.chat.init", {"sandbox_id": sandbox_id})

    with pytest.raises(PermissionError):
        server.call_tool(
            "qso.chat.fork",
            {
                "sandbox_id": sandbox_id,
                "source_conversation_id": "main",
                "fork_conversation_id": "x",
                "role": "user",
            },
        )


def test_chat_summarize_and_fork_parent_hash(tmp_path: Path) -> None:
    server = _server(tmp_path)
    sandbox_id = server.call_tool("qso.create_sandbox", {"session_token": "chat-summary"})["sandbox_id"]
    server.call_tool("qso.chat.init", {"sandbox_id": sandbox_id})

    server.call_tool(
        "qso.chat.append",
        {
            "sandbox_id": sandbox_id,
            "author": "jacob",
            "role": "user",
            "content": "first input",
        },
    )
    server.call_tool(
        "qso.chat.append",
        {
            "sandbox_id": sandbox_id,
            "author": "assistant-1",
            "role": "assistant",
            "content": "first output",
        },
    )
    summary = server.call_tool(
        "qso.chat.summarize",
        {"sandbox_id": sandbox_id, "author": "assistant-1", "role": "assistant"},
    )
    assert summary["result"]["event"]["object_uri"].endswith("/conversation/main")

    fork = server.call_tool(
        "qso.chat.fork",
        {
            "sandbox_id": sandbox_id,
            "source_conversation_id": "main",
            "fork_conversation_id": "branch-a",
            "role": "system",
        },
    )
    assert "parent_hash" in fork["result"]


def test_chat_verify_tool_reports_signed_messages(tmp_path: Path) -> None:
    server = _server(tmp_path)
    sandbox_id = server.call_tool("qso.create_sandbox", {"session_token": "chat-verify"})["sandbox_id"]
    server.call_tool("qso.chat.init", {"sandbox_id": sandbox_id})
    server.call_tool(
        "qso.chat.append",
        {
            "sandbox_id": sandbox_id,
            "author": "jacob",
            "role": "user",
            "content": "verify me",
        },
    )

    verified = server.call_tool(
        "qso.chat.verify",
        {
            "sandbox_id": sandbox_id,
            "strict": True,
        },
    )
    audit = verified["result"]["audit"]
    assert audit["total_messages"] >= 1
    assert audit["failed_messages"] == 0


def test_chat_persists_across_server_instances(tmp_path: Path) -> None:
    server_a = _server(tmp_path)
    sandbox_id = server_a.call_tool("qso.create_sandbox", {"session_token": "shared-session"})["sandbox_id"]
    server_a.call_tool("qso.chat.init", {"sandbox_id": sandbox_id})
    server_a.call_tool(
        "qso.chat.append",
        {
            "sandbox_id": sandbox_id,
            "author": "agent-a",
            "role": "assistant",
            "content": "persist this message",
        },
    )

    server_b = _server(tmp_path)
    sandbox_b = server_b.call_tool("qso.create_sandbox", {"session_token": "shared-session"})["sandbox_id"]
    assert sandbox_b == sandbox_id

    tail = server_b.call_tool("qso.chat.tail", {"sandbox_id": sandbox_b, "limit": 10})
    contents = [m.get("content") for m in tail["messages"]]
    assert "persist this message" in contents
