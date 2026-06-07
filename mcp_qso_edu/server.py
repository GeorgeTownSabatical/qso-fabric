from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp_qso_edu.apc_fabric_edu import APCFabricEduEngine
from mcp_qso_edu.crypto import Identity
from mcp_qso_edu.crypto import verify as verify_signature
from mcp_qso_edu.experiment_isolation import rewrite_uri
from mcp_qso_edu.permissions import PermissionSet, require_action
from mcp_qso_edu.rate_limiter import RateLimitConfig
from mcp_qso_edu.sandbox_engine import SandboxStateEngine
from mcp_qso_edu.schema_registry import SchemaRegistry
from mcp_qso_edu.summarizer import summarize
from mcp_qso_edu.tutorial_engine import TutorialEngine


class QSOEduMCPServer:
    """Sandbox-only educational MCP server for QSO experimentation."""

    def __init__(
        self,
        *,
        schema_registry: SchemaRegistry | None = None,
        tutorial_engine: TutorialEngine | None = None,
        apc_engine: APCFabricEduEngine | None = None,
        permissions: PermissionSet | None = None,
        rate_limit_config: RateLimitConfig | None = None,
        identities: dict[str, Identity] | None = None,
        state_root: str | Path = ".codex/state/mcp_qso_edu/sandboxes",
        apc_state_root: str | Path = ".codex/state/mcp_qso_edu/apc_fabric_edu",
    ) -> None:
        self.schema_registry = schema_registry or SchemaRegistry()
        self.tutorial_engine = tutorial_engine or TutorialEngine()
        self.apc_engine = apc_engine or APCFabricEduEngine(state_root=apc_state_root)
        self.permissions = permissions or PermissionSet.default()
        self.identities = dict(identities or {})
        self.auto_summary_interval = 10
        self.audit_interval = 20
        self.engine = SandboxStateEngine(
            schema_registry=self.schema_registry,
            rate_limit_config=rate_limit_config,
            state_root=state_root,
        )

    def create_sandbox(self, session_token: str) -> dict[str, Any]:
        sandbox_id = self.engine.open(session_token, permissions=self.permissions)
        return {
            "sandbox_id": sandbox_id,
            "capabilities": sorted(cap.value for cap in self.permissions.capabilities),
            "namespaced_prefix": f"qso://sandbox/{sandbox_id}/",
        }

    def qso_create(self, sandbox_id: str, uri: str, schema: dict[str, Any]) -> dict[str, Any]:
        result = self.engine.create(sandbox_id, uri, schema)
        return self.tutorial_engine.annotate("create", result)

    def qso_read(self, sandbox_id: str, uri: str) -> dict[str, Any]:
        result = self.engine.read(sandbox_id, uri)
        return self.tutorial_engine.annotate("read", result)

    def qso_patch(self, sandbox_id: str, uri: str, delta: dict[str, Any], *, actor: str = "sandbox-agent") -> dict[str, Any]:
        result = self.engine.patch(sandbox_id, uri, delta, actor=actor)
        return self.tutorial_engine.annotate("patch", result)

    def qso_timeline(self, sandbox_id: str, uri: str) -> dict[str, Any]:
        result = self.engine.timeline(sandbox_id, uri)
        return self.tutorial_engine.annotate("timeline", result)

    def qso_entangle(self, sandbox_id: str, uri_a: str, uri_b: str, relationship: str) -> dict[str, Any]:
        result = self.engine.entangle(sandbox_id, uri_a, uri_b, relationship)
        return self.tutorial_engine.annotate("entangle", result)

    def qso_export_snapshot(self, sandbox_id: str, uri: str) -> dict[str, Any]:
        result = self.engine.export_snapshot(sandbox_id, uri)
        return self.tutorial_engine.annotate("export_snapshot", result)

    def qso_subscribe(self, sandbox_id: str, uri: str):
        result = self.engine.subscribe(sandbox_id, uri)
        return self.tutorial_engine.annotate("subscribe", {"stream": result})

    def qso_chat_open(self, sandbox_id: str, conversation_id: str = "main") -> dict[str, Any]:
        chat_uri = self._ensure_chat_object(sandbox_id, conversation_id)
        result = self.engine.read(sandbox_id, chat_uri)
        return self.tutorial_engine.annotate("chat_open", {"uri": chat_uri, "qso": result})

    def qso_chat_init(self, sandbox_id: str, conversation_id: str = "main") -> dict[str, Any]:
        normalized = str(conversation_id).strip() or "main"
        chat_uri = rewrite_uri(sandbox_id, f"qso://conversation/{normalized}")
        created = False
        try:
            result = self.engine.read(sandbox_id, chat_uri)
        except KeyError:
            chat_uri = self._ensure_chat_object(sandbox_id, normalized)
            result = self.engine.read(sandbox_id, chat_uri)
            created = True
        return self.tutorial_engine.annotate(
            "chat_init",
            {"uri": chat_uri, "created": created, "qso": result},
        )

    def qso_chat_append(
        self,
        sandbox_id: str,
        *,
        conversation_id: str = "main",
        author: str,
        role: str,
        content: str,
        actor: str = "chat-bridge",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        chat_uri = self._ensure_chat_object(sandbox_id, conversation_id)
        current = self.engine.read(sandbox_id, chat_uri)
        state = dict(current.get("state_layer", {}))
        messages = list(state.get("messages", []))
        allowed_roles = {"user", "assistant", "agent", "system"}
        normalized_role = str(role).strip()
        if normalized_role not in allowed_roles:
            raise ValueError(f"unsupported role: {normalized_role}")
        require_action(normalized_role, "append")

        message = {
            "id": uuid.uuid4().hex,
            "author": str(author),
            "role": normalized_role,
            "content": str(content),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "meta": metadata or {},
        }
        identity = self._identity_for(message["author"])
        message["proof"] = identity.sign(message)
        messages.append(message)
        patch_event = self.engine.patch(
            sandbox_id,
            chat_uri,
            {
                "conversation_id": conversation_id,
                "messages": messages,
                "message_count": len(messages),
                "last_message_id": message["id"],
            },
            actor=actor,
        )
        summary_event = None
        if self._should_auto_summarize(messages, message):
            summary_event = self._append_summary_message(
                sandbox_id=sandbox_id,
                conversation_id=conversation_id,
                messages=messages,
                author="system",
                role="system",
                actor="system",
            )
        audit_event = None
        if len(messages) > 0 and len(messages) % self.audit_interval == 0:
            audit_result = self._audit_messages(messages, strict=False)
            audit_event = self.engine.patch(
                sandbox_id,
                chat_uri,
                {
                    "conversation_id": conversation_id,
                    "last_audit": {
                        **audit_result,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                },
                actor="audit-system",
            )
        return self.tutorial_engine.annotate(
            "chat_append",
            {
                "uri": chat_uri,
                "message": message,
                "event": patch_event,
                "auto_summary_event": summary_event,
                "audit_event": audit_event,
            },
        )

    def qso_chat_read(self, sandbox_id: str, *, conversation_id: str = "main") -> dict[str, Any]:
        chat_uri = self._ensure_chat_object(sandbox_id, conversation_id)
        current = self.engine.read(sandbox_id, chat_uri)
        state = dict(current.get("state_layer", {}))
        messages = list(state.get("messages", []))
        audit = self._audit_messages(messages, strict=False)
        return self.tutorial_engine.annotate(
            "chat_read",
            {
                "uri": chat_uri,
                "messages": messages,
                "message_count": int(state.get("message_count", len(messages))),
                "audit": audit,
            },
        )

    def qso_chat_tail(self, sandbox_id: str, *, conversation_id: str = "main", limit: int = 20) -> dict[str, Any]:
        read = self.qso_chat_read(sandbox_id, conversation_id=conversation_id)
        payload = dict(read["result"])
        messages = list(payload.get("messages", []))
        bounded = max(1, min(500, int(limit)))
        tail = messages[-bounded:]
        return self.tutorial_engine.annotate(
            "chat_tail",
            {
                "uri": payload["uri"],
                "messages": tail,
                "limit": bounded,
                "message_count": len(messages),
            },
        )

    def qso_chat_export_markdown(self, sandbox_id: str, *, conversation_id: str = "main") -> dict[str, Any]:
        read = self.qso_chat_read(sandbox_id, conversation_id=conversation_id)
        payload = dict(read["result"])
        lines = [f"# Conversation {conversation_id}", ""]
        for msg in payload.get("messages", []):
            role = str(msg.get("role", "assistant"))
            author = str(msg.get("author", "unknown"))
            ts = str(msg.get("timestamp", ""))
            content = str(msg.get("content", ""))
            lines.append(f"## {role} ({author})")
            if ts:
                lines.append(f"`{ts}`")
            lines.append("")
            lines.append(content)
            lines.append("")
        return self.tutorial_engine.annotate(
            "chat_export_markdown",
            {
                "uri": payload["uri"],
                "markdown": "\n".join(lines).strip() + "\n",
                "message_count": payload.get("message_count", 0),
            },
        )

    def qso_chat_summarize(
        self,
        sandbox_id: str,
        *,
        conversation_id: str = "main",
        author: str,
        role: str,
        actor: str = "system",
    ) -> dict[str, Any]:
        require_action(str(role), "summarize")
        chat_uri = self._ensure_chat_object(sandbox_id, conversation_id)
        current = self.engine.read(sandbox_id, chat_uri)
        state = dict(current.get("state_layer", {}))
        messages = list(state.get("messages", []))
        event = self._append_summary_message(
            sandbox_id=sandbox_id,
            conversation_id=conversation_id,
            messages=messages,
            author=author,
            role=role,
            actor=actor,
        )
        return self.tutorial_engine.annotate(
            "chat_summarize",
            {
                "uri": chat_uri,
                "event": event,
            },
        )

    def qso_chat_verify(self, sandbox_id: str, *, conversation_id: str = "main", strict: bool = False) -> dict[str, Any]:
        chat_uri = self._ensure_chat_object(sandbox_id, conversation_id)
        current = self.engine.read(sandbox_id, chat_uri)
        state = dict(current.get("state_layer", {}))
        messages = list(state.get("messages", []))
        audit = self._audit_messages(messages, strict=bool(strict))
        return self.tutorial_engine.annotate(
            "chat_verify",
            {
                "uri": chat_uri,
                "strict": bool(strict),
                "audit": audit,
            },
        )

    def qso_chat_fork(
        self,
        sandbox_id: str,
        *,
        source_conversation_id: str,
        fork_conversation_id: str,
        after_index: int | None = None,
        actor: str = "chat-bridge",
        role: str = "system",
    ) -> dict[str, Any]:
        require_action(str(role), "fork")
        source_uri = self._ensure_chat_object(sandbox_id, source_conversation_id)
        source = self.engine.read(sandbox_id, source_uri)
        source_state = dict(source.get("state_layer", {}))
        source_messages = list(source_state.get("messages", []))
        if after_index is not None:
            start = max(0, int(after_index))
            source_messages = source_messages[start:]
        parent_hash = hashlib.sha256(json.dumps(source_messages, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

        fork_uri = self._ensure_chat_object(sandbox_id, fork_conversation_id)
        event = self.engine.patch(
            sandbox_id,
            fork_uri,
            {
                "conversation_id": fork_conversation_id,
                "forked_from": source_conversation_id,
                "parent_hash": parent_hash,
                "messages": source_messages,
                "message_count": len(source_messages),
            },
            actor=actor,
        )
        return self.tutorial_engine.annotate(
            "chat_fork",
            {
                "source_uri": source_uri,
                "fork_uri": fork_uri,
                "copied_messages": len(source_messages),
                "parent_hash": parent_hash,
                "event": event,
            },
        )

    def qso_chat_subscribe(self, sandbox_id: str, *, conversation_id: str = "main"):
        chat_uri = self._ensure_chat_object(sandbox_id, conversation_id)
        result = self.engine.subscribe(sandbox_id, chat_uri)
        return self.tutorial_engine.annotate("chat_subscribe", {"uri": chat_uri, "stream": result})

    def qso_edu_apc_bootstrap(
        self,
        sandbox_id: str,
        *,
        mode: str = "exhaustive",
        domain: str = "physics",
        baseline_models: list[str] | None = None,
        owner: str = "community",
    ) -> dict[str, Any]:
        self.engine.sandbox_status(sandbox_id)
        result = self.apc_engine.bootstrap_bundle(
            sandbox_id=sandbox_id,
            mode=mode,
            domain=domain,
            baseline_models=baseline_models,
            owner=owner,
        )
        return self.tutorial_engine.annotate("apc_bootstrap", result)

    def qso_edu_apc_runs(self, sandbox_id: str) -> dict[str, Any]:
        self.engine.sandbox_status(sandbox_id)
        result = self.apc_engine.list_runs(sandbox_id=sandbox_id)
        return self.tutorial_engine.annotate("apc_runs", result)

    def qso_edu_apc_audit(self, sandbox_id: str, *, mode: str = "standard") -> dict[str, Any]:
        self.engine.sandbox_status(sandbox_id)
        result = self.apc_engine.generate_reproducible_audit(mode=mode)
        return self.tutorial_engine.annotate("apc_audit", result)

    def qso_edu_apc_resources(self) -> dict[str, Any]:
        return self.tutorial_engine.annotate(
            "apc_resources",
            {
                "checklist_template": self.apc_engine.speculative_checklist_template(),
                "scorecard_template": self.apc_engine.falsifiability_scorecard_template(model_name="APC"),
                "teaching_pipeline": self.apc_engine.teaching_pipeline(),
                "comparison_harness_template": self.apc_engine.comparison_harness(
                    "APC",
                    ["LambdaCDM+SM", "EFT-agnostic baseline"],
                ),
                "misinformation_controls": self.apc_engine.misinformation_controls(),
                "scientific_method_framework": self.apc_engine.scientific_method_framework(domain="physics"),
                "red_team_pack_template": self.apc_engine.red_team_pack(),
            },
        )

    def list_schemas(self) -> dict[str, Any]:
        return self.schema_registry.list_schemas()

    def list_tutorials(self) -> list[dict[str, str]]:
        return self.tutorial_engine.tutorials()

    def examples(self) -> list[dict[str, Any]]:
        return [
            {
                "tool": "qso.create",
                "input": {"uri": "qso://sandbox/my_object", "schema": self.schema_registry.get("object")},
            },
            {
                "tool": "qso.patch",
                "input": {"uri": "qso://sandbox/my_object", "delta": {"tick": 1}},
            },
        ]

    def status(self, sandbox_id: str) -> dict[str, Any]:
        return self.engine.sandbox_status(sandbox_id)

    def _identity_for(self, author: str) -> Identity:
        normalized = str(author).strip() or "unknown"
        identity = self.identities.get(normalized)
        if identity is None:
            identity = Identity.from_seed_text(normalized, f"qso-edu::{normalized}")
            self.identities[normalized] = identity
        return identity

    def _should_auto_summarize(self, messages: list[dict[str, Any]], latest: dict[str, Any]) -> bool:
        latest_meta = latest.get("meta", {})
        if isinstance(latest_meta, dict) and latest_meta.get("type") == "summary":
            return False
        count = 0
        for item in messages:
            role = str(item.get("role", ""))
            meta = item.get("meta", {})
            if role in {"user", "assistant"} and not (isinstance(meta, dict) and meta.get("type") == "summary"):
                count += 1
        return count > 0 and count % self.auto_summary_interval == 0

    def _append_summary_message(
        self,
        *,
        sandbox_id: str,
        conversation_id: str,
        messages: list[dict[str, Any]],
        author: str,
        role: str,
        actor: str,
    ) -> dict[str, Any] | None:
        summary_text = summarize(messages)
        if not summary_text:
            return None
        summary_message = {
            "id": uuid.uuid4().hex,
            "author": str(author),
            "role": "system",
            "content": summary_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "meta": {"type": "summary", "window": min(len(messages), 40), "trigger_role": str(role)},
        }
        summary_message["proof"] = self._identity_for(summary_message["author"]).sign(summary_message)
        next_messages = [*messages, summary_message]
        return self.engine.patch(
            sandbox_id,
            self._ensure_chat_object(sandbox_id, conversation_id),
            {
                "conversation_id": conversation_id,
                "messages": next_messages,
                "message_count": len(next_messages),
                "last_message_id": summary_message["id"],
            },
            actor=actor,
        )

    def _audit_messages(self, messages: list[dict[str, Any]], *, strict: bool) -> dict[str, Any]:
        total = len(messages)
        verified = 0
        unsigned = 0
        failed_ids: list[str] = []

        for message in messages:
            message_id = str(message.get("id", ""))
            proof = message.get("proof")
            if not isinstance(proof, dict):
                unsigned += 1
                if strict:
                    failed_ids.append(message_id)
                continue

            payload = {k: v for k, v in message.items() if k != "proof"}
            try:
                if verify_signature(payload, proof):
                    verified += 1
                else:
                    failed_ids.append(message_id)
            except Exception:
                failed_ids.append(message_id)

        return {
            "total_messages": total,
            "verified_messages": verified,
            "unsigned_messages": unsigned,
            "failed_messages": len(failed_ids),
            "failed_ids": failed_ids,
        }

    def _ensure_chat_object(self, sandbox_id: str, conversation_id: str) -> str:
        normalized = str(conversation_id).strip() or "main"
        uri = rewrite_uri(sandbox_id, f"qso://conversation/{normalized}")
        try:
            self.engine.read(sandbox_id, uri)
        except KeyError:
            self.engine.create(sandbox_id, uri, self.schema_registry.get("conversation"))
            self.engine.patch(
                sandbox_id,
                uri,
                {
                    "conversation_id": normalized,
                    "messages": [],
                    "message_count": 0,
                },
                actor="chat-system",
            )
        return uri
