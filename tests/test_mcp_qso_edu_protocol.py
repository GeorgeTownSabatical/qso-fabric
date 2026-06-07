from __future__ import annotations

import json
from pathlib import Path

from mcp_qso_edu.conversation_bridge import ConversationBridge
from mcp_qso_edu.protocol_server import QSOEduMCPProtocolServer
from mcp_qso_edu.upstream_apps import UpstreamAppBridge


def test_protocol_tools_call_roundtrip(tmp_path: Path) -> None:
    server = QSOEduMCPProtocolServer(
        conversation_bridge=ConversationBridge(tmp_path / "bridge.jsonl"),
        state_root=tmp_path / "sandboxes",
    )

    init = server.handle_request({"method": "initialize", "params": {}})
    assert init["serverInfo"]["name"] == "qso-edu-mcp"

    listed = server.handle_request({"method": "tools/list", "params": {}})
    tool_names = {tool["name"] for tool in listed["tools"]}
    assert "qso.create_sandbox" in tool_names
    assert "qso.create" in tool_names

    sandbox = server.handle_request(
        {
            "method": "tools/call",
            "params": {
                "name": "qso.create_sandbox",
                "arguments": {"session_token": "proto-test"},
            },
        }
    )
    sandbox_id = sandbox["content"][0]["json"]["sandbox_id"]

    created = server.handle_request(
        {
            "method": "tools/call",
            "params": {
                "name": "qso.create",
                "arguments": {
                    "sandbox_id": sandbox_id,
                    "uri": "qso://demo/object",
                    "schema": {"type": "object"},
                },
            },
        }
    )
    uri = created["content"][0]["json"]["result"]["uri"]
    assert uri.startswith(f"qso://sandbox/{sandbox_id}/")


def test_protocol_resources_read_status(tmp_path: Path) -> None:
    server = QSOEduMCPProtocolServer(
        conversation_bridge=ConversationBridge(tmp_path / "bridge.jsonl"),
        state_root=tmp_path / "sandboxes",
    )
    sandbox = server.call_tool("qso.create_sandbox", {"session_token": "resource-test"})
    sandbox_id = sandbox["sandbox_id"]

    resources = server.handle_request({"method": "resources/list", "params": {}})
    uris = {row["uri"] for row in resources["resources"]}
    assert "qso://edu/status" in uris

    status = server.handle_request(
        {
            "method": "resources/read",
            "params": {
                "uri": "qso://edu/status",
                "arguments": {"sandbox_id": sandbox_id},
            },
        }
    )
    payload = json.loads(status["contents"][0]["text"])
    assert payload["sandbox_id"] == sandbox_id


def test_upstream_app_bridge_tools_and_call(tmp_path: Path) -> None:
    class FakeUpstreamBridge(UpstreamAppBridge):
        def __init__(self) -> None:
            super().__init__({})

        def has_apps(self) -> bool:
            return True

        def list_apps(self) -> list[dict]:
            return [{"name": "fake", "command": ["fake"]}]

        def list_tools(self, app: str) -> list[dict]:
            assert app == "fake"
            return [{"name": "demo.echo", "inputSchema": {"type": "object"}}]

        def call_tool(self, app: str, name: str, arguments: dict | None = None) -> dict:
            assert app == "fake"
            assert name == "demo.echo"
            return {"content": [{"type": "json", "json": {"echo": arguments or {}}}]}

        def close(self) -> None:
            return None

    server = QSOEduMCPProtocolServer(
        enable_upstream_apps=True,
        upstream_bridge=FakeUpstreamBridge(),
        conversation_bridge=ConversationBridge(tmp_path / "bridge.jsonl"),
        state_root=tmp_path / "sandboxes",
    )
    listed = server.call_tool("mcp.apps.list", {})
    assert listed["apps"][0]["name"] == "fake"

    tools = server.call_tool("mcp.apps.tools", {"app": "fake"})
    assert tools["tools"][0]["name"] == "demo.echo"

    called = server.call_tool(
        "mcp.apps.call",
        {"app": "fake", "tool": "demo.echo", "arguments": {"value": 7}},
    )
    echo = called["result"]["content"][0]["json"]["echo"]
    assert echo["value"] == 7
    server.close()


def test_bridge_append_and_read_tools(tmp_path: Path) -> None:
    server = QSOEduMCPProtocolServer(
        conversation_bridge=ConversationBridge(tmp_path / "bridge.jsonl"),
        state_root=tmp_path / "sandboxes",
    )
    appended = server.call_tool(
        "bridge.append_message",
        {
            "source": "chatgpt_plus",
            "content": "hello relay",
            "session_id": "triad",
            "metadata": {"role": "user"},
        },
    )
    assert appended["seq"] == 1

    read = server.call_tool("bridge.read_messages", {"after_seq": 0, "limit": 10})
    assert len(read["messages"]) == 1
    assert read["messages"][0]["content"] == "hello relay"


def test_qso_chat_tools_append_read_and_fork(tmp_path: Path) -> None:
    server = QSOEduMCPProtocolServer(
        conversation_bridge=ConversationBridge(tmp_path / "bridge.jsonl"),
        state_root=tmp_path / "sandboxes",
    )
    sandbox_id = server.call_tool("qso.create_sandbox", {"session_token": "chat-test"})["sandbox_id"]

    opened = server.call_tool(
        "qso.chat.open",
        {"sandbox_id": sandbox_id, "conversation_id": "main"},
    )
    assert opened["result"]["uri"].endswith("/conversation/main")

    server.call_tool(
        "qso.chat.append",
        {
            "sandbox_id": sandbox_id,
            "conversation_id": "main",
            "author": "chatgpt_plus",
            "role": "assistant",
            "content": "first message",
        },
    )
    server.call_tool(
        "qso.chat.append",
        {
            "sandbox_id": sandbox_id,
            "conversation_id": "main",
            "author": "codex",
            "role": "assistant",
            "content": "second message",
        },
    )

    read = server.call_tool(
        "qso.chat.read",
        {"sandbox_id": sandbox_id, "conversation_id": "main"},
    )
    assert read["result"]["message_count"] == 2
    assert read["result"]["messages"][0]["content"] == "first message"

    forked = server.call_tool(
        "qso.chat.fork",
        {
            "sandbox_id": sandbox_id,
            "source_conversation_id": "main",
            "fork_conversation_id": "branch-a",
            "after_index": 1,
        },
    )
    assert forked["result"]["copied_messages"] == 1


def test_qso_edu_apc_tools_bootstrap_runs_and_resources(tmp_path: Path) -> None:
    server = QSOEduMCPProtocolServer(
        conversation_bridge=ConversationBridge(tmp_path / "bridge.jsonl"),
        state_root=tmp_path / "sandboxes",
    )
    sandbox_id = server.call_tool("qso.create_sandbox", {"session_token": "apc-bundle"})["sandbox_id"]

    bootstrap = server.call_tool(
        "qso.edu.apc.bootstrap",
        {
            "sandbox_id": sandbox_id,
            "mode": "quick",
            "domain": "physics",
            "baseline_models": ["LambdaCDM+SM", "Toy-EFT"],
            "owner": "test-suite",
        },
    )
    payload = bootstrap["result"]
    assert payload["artifact_count"] >= 10
    assert payload["mode"] == "quick"
    run_path = Path(payload["run_path"])
    assert run_path.exists()
    assert (run_path / "manifest.json").exists()
    assert (run_path / "validation" / "apc_bayes_comparison_latest.json").exists()
    assert "bayes_factor_summary" in payload

    runs = server.call_tool("qso.edu.apc.runs", {"sandbox_id": sandbox_id})
    assert runs["result"]["runs"]
    assert runs["result"]["runs"][0]["has_manifest"] is True

    audit = server.call_tool("qso.edu.apc.audit", {"sandbox_id": sandbox_id, "mode": "quick"})
    assert audit["result"]["mode"] == "quick"
    assert audit["result"]["dimension_check"]["mismatch_count"] == 0

    resources = server.call_tool("qso.edu.apc.resources", {})
    assert "Speculative Model Checklist" in resources["result"]["checklist_template"]

    resource_payload = server.read_resource("qso://edu/apc", {})
    assert resource_payload["action"] == "apc_resources"
