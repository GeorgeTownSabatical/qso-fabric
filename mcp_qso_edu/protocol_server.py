from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from mcp_qso_edu.chat_tools import append_message, init_conversation, tail_messages
from mcp_qso_edu.conversation_bridge import ConversationBridge
from mcp_qso_edu.server import QSOEduMCPServer
from mcp_qso_edu.upstream_apps import UpstreamAppBridge


@dataclass(frozen=True, slots=True)
class MCPToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


class QSOEduMCPProtocolServer:
    """MCP-style adapter for the educational sandbox server."""

    def __init__(
        self,
        app: QSOEduMCPServer | None = None,
        *,
        enable_upstream_apps: bool = False,
        upstream_bridge: UpstreamAppBridge | None = None,
        conversation_bridge: ConversationBridge | None = None,
        state_root: str | Path = ".codex/state/mcp_qso_edu/sandboxes",
    ) -> None:
        self.app = app or QSOEduMCPServer(state_root=state_root)
        self.upstream_bridge = upstream_bridge or UpstreamAppBridge.from_env()
        self.enable_upstream_apps = bool(enable_upstream_apps and self.upstream_bridge.has_apps())
        self.conversation_bridge = conversation_bridge or ConversationBridge()

        self._tool_specs = self._build_tool_specs(self.enable_upstream_apps)
        self._tool_handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "qso.create_sandbox": self._tool_create_sandbox,
            "qso.create": self._tool_qso_create,
            "qso.read": self._tool_qso_read,
            "qso.patch": self._tool_qso_patch,
            "qso.timeline": self._tool_qso_timeline,
            "qso.entangle": self._tool_qso_entangle,
            "qso.export_snapshot": self._tool_qso_export_snapshot,
            "qso.subscribe": self._tool_qso_subscribe,
            "qso.status": self._tool_qso_status,
            "qso.chat.init": self._tool_qso_chat_init,
            "qso.chat.open": self._tool_qso_chat_open,
            "qso.chat.append": self._tool_qso_chat_append,
            "qso.chat.tail": self._tool_qso_chat_tail,
            "qso.chat.export_markdown": self._tool_qso_chat_export_markdown,
            "qso.chat.summarize": self._tool_qso_chat_summarize,
            "qso.chat.verify": self._tool_qso_chat_verify,
            "qso.chat.read": self._tool_qso_chat_read,
            "qso.chat.fork": self._tool_qso_chat_fork,
            "qso.chat.subscribe": self._tool_qso_chat_subscribe,
            "qso.edu.apc.bootstrap": self._tool_qso_edu_apc_bootstrap,
            "qso.edu.apc.runs": self._tool_qso_edu_apc_runs,
            "qso.edu.apc.audit": self._tool_qso_edu_apc_audit,
            "qso.edu.apc.resources": self._tool_qso_edu_apc_resources,
            "bridge.append_message": self._tool_bridge_append_message,
            "bridge.read_messages": self._tool_bridge_read_messages,
        }
        if self.enable_upstream_apps:
            self._tool_handlers["mcp.apps.list"] = self._tool_mcp_apps_list
            self._tool_handlers["mcp.apps.tools"] = self._tool_mcp_apps_tools
            self._tool_handlers["mcp.apps.call"] = self._tool_mcp_apps_call

    def initialize(self) -> dict[str, Any]:
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "qso-edu-mcp",
                "version": "0.1.0",
            },
            "capabilities": {
                "tools": {},
                "resources": {},
            },
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "inputSchema": spec.input_schema,
            }
            for spec in self._tool_specs
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        handler = self._tool_handlers.get(name)
        if handler is None:
            raise KeyError(f"unknown tool: {name}")
        return handler(arguments or {})

    def list_resources(self) -> list[dict[str, str]]:
        return [
            {
                "uri": "qso://edu/schemas",
                "name": "QSO sandbox schemas",
                "description": "Schema templates available in the educational sandbox.",
                "mimeType": "application/json",
            },
            {
                "uri": "qso://edu/tutorials",
                "name": "QSO tutorials",
                "description": "Stepwise educational explanations for sandbox operations.",
                "mimeType": "application/json",
            },
            {
                "uri": "qso://edu/examples",
                "name": "QSO examples",
                "description": "Ready-to-run tool invocation examples.",
                "mimeType": "application/json",
            },
            {
                "uri": "qso://edu/status",
                "name": "Sandbox status",
                "description": "Rate-limit and capability status for one sandbox_id.",
                "mimeType": "application/json",
            },
            {
                "uri": "qso://edu/apc",
                "name": "APC educational framework",
                "description": "APC templates, scorecards, controls, and scientific-method scaffolds.",
                "mimeType": "application/json",
            },
        ]

    def read_resource(self, uri: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized = str(uri).strip()
        params = params or {}

        if normalized == "qso://edu/schemas":
            return self.app.list_schemas()
        if normalized == "qso://edu/tutorials":
            return {"tutorials": self.app.list_tutorials()}
        if normalized == "qso://edu/examples":
            return {"examples": self.app.examples()}
        if normalized == "qso://edu/status":
            sandbox_id = self._required_str(params, "sandbox_id")
            return self.app.status(sandbox_id)
        if normalized == "qso://edu/apc":
            return self.app.qso_edu_apc_resources()

        raise KeyError(f"unknown resource: {normalized}")

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        method = str(request.get("method", "")).strip()
        params = request.get("params", {})
        if not isinstance(params, dict):
            raise TypeError("params must be an object")

        if method == "initialize":
            return self.initialize()
        if method == "tools/list":
            return {"tools": self.list_tools()}
        if method == "tools/call":
            name = self._required_str(params, "name")
            arguments = params.get("arguments", {})
            if not isinstance(arguments, dict):
                raise TypeError("tools/call arguments must be an object")
            return {"content": [{"type": "json", "json": self.call_tool(name, arguments)}]}
        if method == "resources/list":
            return {"resources": self.list_resources()}
        if method == "resources/read":
            uri = self._required_str(params, "uri")
            arguments = params.get("arguments", {})
            if not isinstance(arguments, dict):
                raise TypeError("resources/read arguments must be an object")
            body = self.read_resource(uri, arguments)
            return {"contents": [{"uri": uri, "mimeType": "application/json", "text": self._compact_json(body)}]}
        if method in {"shutdown", "exit"}:
            return {"ok": True}

        raise KeyError(f"unsupported method: {method}")

    def _tool_create_sandbox(self, arguments: dict[str, Any]) -> dict[str, Any]:
        session_token = self._required_str(arguments, "session_token")
        return self.app.create_sandbox(session_token)

    def _tool_qso_create(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        uri = self._required_str(arguments, "uri")
        schema = self._required_dict(arguments, "schema")
        return self.app.qso_create(sandbox_id, uri, schema)

    def _tool_qso_read(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        uri = self._required_str(arguments, "uri")
        return self.app.qso_read(sandbox_id, uri)

    def _tool_qso_patch(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        uri = self._required_str(arguments, "uri")
        delta = self._required_dict(arguments, "delta")
        actor = str(arguments.get("actor", "sandbox-agent"))
        return self.app.qso_patch(sandbox_id, uri, delta, actor=actor)

    def _tool_qso_timeline(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        uri = self._required_str(arguments, "uri")
        return self.app.qso_timeline(sandbox_id, uri)

    def _tool_qso_entangle(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        uri_a = self._required_str(arguments, "uri_a")
        uri_b = self._required_str(arguments, "uri_b")
        relationship = self._required_str(arguments, "relationship")
        return self.app.qso_entangle(sandbox_id, uri_a, uri_b, relationship)

    def _tool_qso_export_snapshot(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        uri = self._required_str(arguments, "uri")
        return self.app.qso_export_snapshot(sandbox_id, uri)

    def _tool_qso_subscribe(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        uri = self._required_str(arguments, "uri")
        # Async streaming is available through Python API; stdio bridge returns an explicit contract.
        return {
            "status": "streaming_not_supported_in_stdio_bridge",
            "next": "Use Python API server.qso_subscribe(...) for async stream consumption.",
            "sandbox_id": sandbox_id,
            "uri": uri,
        }

    def _tool_qso_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        return self.app.status(sandbox_id)

    def _tool_qso_edu_apc_bootstrap(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        mode = str(arguments.get("mode", "exhaustive"))
        domain = str(arguments.get("domain", "physics"))
        owner = str(arguments.get("owner", "community"))
        baseline_models_raw = arguments.get("baseline_models", [])
        if not isinstance(baseline_models_raw, list):
            raise TypeError("baseline_models must be an array of strings")
        baseline_models = [str(item) for item in baseline_models_raw]
        return self.app.qso_edu_apc_bootstrap(
            sandbox_id,
            mode=mode,
            domain=domain,
            baseline_models=baseline_models or None,
            owner=owner,
        )

    def _tool_qso_edu_apc_runs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        return self.app.qso_edu_apc_runs(sandbox_id)

    def _tool_qso_edu_apc_audit(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        mode = str(arguments.get("mode", "standard"))
        return self.app.qso_edu_apc_audit(sandbox_id, mode=mode)

    def _tool_qso_edu_apc_resources(self, arguments: dict[str, Any]) -> dict[str, Any]:
        _ = arguments
        return self.app.qso_edu_apc_resources()

    def _tool_qso_chat_open(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        conversation_id = str(arguments.get("conversation_id", "main"))
        return self.app.qso_chat_open(sandbox_id, conversation_id=conversation_id)

    def _tool_qso_chat_init(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        conversation_id = str(arguments.get("conversation_id", "main"))
        return init_conversation(self.app, sandbox_id, conversation_id=conversation_id)

    def _tool_qso_chat_append(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        author = self._required_str(arguments, "author")
        role = self._required_str(arguments, "role")
        content = self._required_str(arguments, "content")
        conversation_id = str(arguments.get("conversation_id", "main"))
        actor = str(arguments.get("actor", "chat-bridge"))
        metadata = arguments.get("meta", arguments.get("metadata", {}))
        if not isinstance(metadata, dict):
            raise TypeError("meta must be an object")
        msg = append_message(
            self.app,
            sandbox_id=sandbox_id,
            author=author,
            role=role,
            content=content,
            meta=metadata,
            conversation_id=conversation_id,
        )
        return {"message": msg, "actor": actor}

    def _tool_qso_chat_read(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        conversation_id = str(arguments.get("conversation_id", "main"))
        return self.app.qso_chat_read(sandbox_id, conversation_id=conversation_id)

    def _tool_qso_chat_tail(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        conversation_id = str(arguments.get("conversation_id", "main"))
        limit = int(arguments.get("limit", 20))
        return tail_messages(self.app, sandbox_id, limit=limit, conversation_id=conversation_id)

    def _tool_qso_chat_export_markdown(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        conversation_id = str(arguments.get("conversation_id", "main"))
        return self.app.qso_chat_export_markdown(sandbox_id, conversation_id=conversation_id)

    def _tool_qso_chat_summarize(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        author = self._required_str(arguments, "author")
        role = self._required_str(arguments, "role")
        conversation_id = str(arguments.get("conversation_id", "main"))
        actor = str(arguments.get("actor", author))
        return self.app.qso_chat_summarize(
            sandbox_id,
            conversation_id=conversation_id,
            author=author,
            role=role,
            actor=actor,
        )

    def _tool_qso_chat_verify(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        conversation_id = str(arguments.get("conversation_id", "main"))
        strict = bool(arguments.get("strict", False))
        return self.app.qso_chat_verify(
            sandbox_id,
            conversation_id=conversation_id,
            strict=strict,
        )

    def _tool_qso_chat_fork(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        source_conversation_id = self._required_str(arguments, "source_conversation_id")
        fork_conversation_id = self._required_str(arguments, "fork_conversation_id")
        actor = str(arguments.get("actor", "chat-bridge"))
        role = str(arguments.get("role", "system"))
        after_index = arguments.get("after_index")
        if after_index is not None:
            after_index = int(after_index)
        return self.app.qso_chat_fork(
            sandbox_id,
            source_conversation_id=source_conversation_id,
            fork_conversation_id=fork_conversation_id,
            after_index=after_index,
            actor=actor,
            role=role,
        )

    def _tool_qso_chat_subscribe(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sandbox_id = self._required_str(arguments, "sandbox_id")
        conversation_id = str(arguments.get("conversation_id", "main"))
        opened = self.app.qso_chat_open(sandbox_id, conversation_id=conversation_id)
        uri = opened["result"]["uri"]
        return {
            "status": "streaming_not_supported_in_stdio_bridge",
            "next": "Use Python API server.qso_chat_subscribe(...) for async stream consumption.",
            "sandbox_id": sandbox_id,
            "conversation_id": conversation_id,
            "uri": uri,
        }

    def _tool_bridge_append_message(self, arguments: dict[str, Any]) -> dict[str, Any]:
        source = self._required_str(arguments, "source")
        content = self._required_str(arguments, "content")
        session_id = str(arguments.get("session_id", "shared"))
        metadata = arguments.get("metadata", {})
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be an object")
        return self.conversation_bridge.append(
            source=source,
            content=content,
            session_id=session_id,
            metadata=metadata,
        )

    def _tool_bridge_read_messages(self, arguments: dict[str, Any]) -> dict[str, Any]:
        after_seq = int(arguments.get("after_seq", 0))
        limit = int(arguments.get("limit", 200))
        return self.conversation_bridge.read(after_seq=after_seq, limit=limit)

    def _tool_mcp_apps_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        _ = arguments
        self._require_upstream_enabled()
        return {"apps": self.upstream_bridge.list_apps()}

    def _tool_mcp_apps_tools(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._require_upstream_enabled()
        app = self._required_str(arguments, "app")
        return {"app": app, "tools": self.upstream_bridge.list_tools(app)}

    def _tool_mcp_apps_call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._require_upstream_enabled()
        app = self._required_str(arguments, "app")
        name = self._required_str(arguments, "tool")
        tool_args = arguments.get("arguments", {})
        if not isinstance(tool_args, dict):
            raise TypeError("arguments must be an object")
        result = self.upstream_bridge.call_tool(app, name, tool_args)
        return {
            "app": app,
            "tool": name,
            "result": result,
        }

    def close(self) -> None:
        self.upstream_bridge.close()

    @staticmethod
    def _required_str(data: dict[str, Any], key: str) -> str:
        if key not in data:
            raise KeyError(f"missing required field: {key}")
        value = str(data[key]).strip()
        if not value:
            raise ValueError(f"{key} must be non-empty")
        return value

    @staticmethod
    def _required_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
        if key not in data:
            raise KeyError(f"missing required field: {key}")
        value = data[key]
        if not isinstance(value, dict):
            raise TypeError(f"{key} must be an object")
        return value

    @staticmethod
    def _compact_json(payload: dict[str, Any]) -> str:
        import json

        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _build_tool_specs(enable_upstream_apps: bool) -> tuple[MCPToolSpec, ...]:
        specs: list[MCPToolSpec] = [
            MCPToolSpec(
                name="qso.create_sandbox",
                description="Create or resume a sandbox namespace for a session token.",
                input_schema={
                    "type": "object",
                    "required": ["session_token"],
                    "properties": {"session_token": {"type": "string"}},
                },
            ),
            MCPToolSpec(
                name="qso.create",
                description="Create a sandboxed QSO object.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id", "uri", "schema"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "uri": {"type": "string"},
                        "schema": {"type": "object"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.read",
                description="Read a sandboxed QSO object.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id", "uri"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "uri": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.patch",
                description="Patch a sandboxed QSO object through event-sourced delta mutation.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id", "uri", "delta"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "uri": {"type": "string"},
                        "delta": {"type": "object"},
                        "actor": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.timeline",
                description="Read the deterministic event timeline for a sandbox object.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id", "uri"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "uri": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.entangle",
                description="Create an entanglement edge between two sandbox objects.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id", "uri_a", "uri_b", "relationship"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "uri_a": {"type": "string"},
                        "uri_b": {"type": "string"},
                        "relationship": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.export_snapshot",
                description="Export a base64-encoded snapshot blob for a sandbox object.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id", "uri"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "uri": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.subscribe",
                description="Declare intent to subscribe to sandbox stream updates.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id", "uri"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "uri": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.status",
                description="Read current sandbox capability and rate-limit status.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id"],
                    "properties": {"sandbox_id": {"type": "string"}},
                },
            ),
            MCPToolSpec(
                name="qso.edu.apc.bootstrap",
                description="Generate a full APC educational artifact bundle (all 10 capability tracks).",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "mode": {"type": "string", "enum": ["quick", "standard", "exhaustive"]},
                        "domain": {"type": "string"},
                        "owner": {"type": "string"},
                        "baseline_models": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            ),
            MCPToolSpec(
                name="qso.edu.apc.runs",
                description="List APC educational runs created for a sandbox.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id"],
                    "properties": {"sandbox_id": {"type": "string"}},
                },
            ),
            MCPToolSpec(
                name="qso.edu.apc.audit",
                description="Generate a deterministic APC audit payload without full bundle generation.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "mode": {"type": "string", "enum": ["quick", "standard", "exhaustive"]},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.edu.apc.resources",
                description="Return APC checklist, scorecard, comparison, controls, framework, and red-team templates.",
                input_schema={
                    "type": "object",
                    "properties": {},
                },
            ),
            MCPToolSpec(
                name="qso.chat.init",
                description="Create the canonical sandbox conversation object if missing.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "conversation_id": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.chat.open",
                description="Alias for qso.chat.init.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "conversation_id": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.chat.append",
                description="Append a message into the canonical conversation object.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id", "author", "role", "content"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "conversation_id": {"type": "string"},
                        "author": {"type": "string"},
                        "role": {"type": "string"},
                        "content": {"type": "string"},
                        "actor": {"type": "string"},
                        "meta": {"type": "object"},
                        "metadata": {"type": "object"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.chat.tail",
                description="Read the last N messages from a canonical conversation object.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "conversation_id": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.chat.export_markdown",
                description="Export canonical conversation content as markdown.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "conversation_id": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.chat.summarize",
                description="Generate or update a rolling conversation summary.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id", "author", "role"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "conversation_id": {"type": "string"},
                        "author": {"type": "string"},
                        "role": {"type": "string"},
                        "actor": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.chat.verify",
                description="Verify signed messages in a conversation and return audit results.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "conversation_id": {"type": "string"},
                        "strict": {"type": "boolean"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.chat.read",
                description="Read all messages from a canonical conversation object.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "conversation_id": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.chat.fork",
                description="Fork one conversation into another conversation object.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id", "source_conversation_id", "fork_conversation_id"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "source_conversation_id": {"type": "string"},
                        "fork_conversation_id": {"type": "string"},
                        "after_index": {"type": "integer"},
                        "actor": {"type": "string"},
                        "role": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="qso.chat.subscribe",
                description="Subscribe to live updates for a canonical conversation object.",
                input_schema={
                    "type": "object",
                    "required": ["sandbox_id"],
                    "properties": {
                        "sandbox_id": {"type": "string"},
                        "conversation_id": {"type": "string"},
                    },
                },
            ),
            MCPToolSpec(
                name="bridge.append_message",
                description="Append a message into the shared bridge log between clients.",
                input_schema={
                    "type": "object",
                    "required": ["source", "content"],
                    "properties": {
                        "source": {"type": "string"},
                        "content": {"type": "string"},
                        "session_id": {"type": "string"},
                        "metadata": {"type": "object"},
                    },
                },
            ),
            MCPToolSpec(
                name="bridge.read_messages",
                description="Read shared bridge messages after a sequence id.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "after_seq": {"type": "integer"},
                        "limit": {"type": "integer"},
                    },
                },
            ),
        ]
        if enable_upstream_apps:
            specs.extend(
                (
                    MCPToolSpec(
                        name="mcp.apps.list",
                        description="List configured upstream MCP apps connected by this server.",
                        input_schema={
                            "type": "object",
                            "properties": {},
                        },
                    ),
                    MCPToolSpec(
                        name="mcp.apps.tools",
                        description="List tools exposed by one configured upstream MCP app.",
                        input_schema={
                            "type": "object",
                            "required": ["app"],
                            "properties": {"app": {"type": "string"}},
                        },
                    ),
                    MCPToolSpec(
                        name="mcp.apps.call",
                        description="Call one tool on a configured upstream MCP app.",
                        input_schema={
                            "type": "object",
                            "required": ["app", "tool"],
                            "properties": {
                                "app": {"type": "string"},
                                "tool": {"type": "string"},
                                "arguments": {"type": "object"},
                            },
                        },
                    ),
                )
            )
        return tuple(specs)

    def _require_upstream_enabled(self) -> None:
        if not self.enable_upstream_apps:
            raise PermissionError("upstream MCP app bridge is disabled")
