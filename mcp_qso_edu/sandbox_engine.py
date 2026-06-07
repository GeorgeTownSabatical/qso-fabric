from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator

from api.mcp_tools.qso_tools import QSOMCPTools
from mcp_qso_edu.experiment_isolation import forbidden_root, rewrite_uri, sandbox_id_for_token
from mcp_qso_edu.permissions import Capability, PermissionSet
from mcp_qso_edu.sandbox_persistence import SandboxOperationStore
from mcp_qso_edu.rate_limiter import RateLimitConfig, SlidingWindowRateLimiter
from mcp_qso_edu.schema_registry import SchemaRegistry


@dataclass(slots=True)
class SandboxContext:
    sandbox_id: str
    tools: QSOMCPTools
    permissions: PermissionSet
    limiter: SlidingWindowRateLimiter
    applied_ops: int = 0
    store_path: Path | None = None


class SandboxStateEngine:
    def __init__(
        self,
        *,
        schema_registry: SchemaRegistry | None = None,
        rate_limit_config: RateLimitConfig | None = None,
        state_root: str | Path = ".codex/state/mcp_qso_edu/sandboxes",
    ) -> None:
        self.schema_registry = schema_registry or SchemaRegistry()
        self.rate_limit_config = rate_limit_config or RateLimitConfig()
        self.store = SandboxOperationStore(state_root)
        self._sandboxes: dict[str, SandboxContext] = {}

    def open(self, session_token: str, permissions: PermissionSet | None = None) -> str:
        sandbox_id = sandbox_id_for_token(session_token)
        if sandbox_id not in self._sandboxes:
            self._sandboxes[sandbox_id] = SandboxContext(
                sandbox_id=sandbox_id,
                tools=QSOMCPTools(),
                permissions=permissions or PermissionSet.default(),
                limiter=SlidingWindowRateLimiter(self.rate_limit_config),
                store_path=self.store.path_for(sandbox_id),
            )
        self._refresh(self._sandboxes[sandbox_id])
        return sandbox_id

    def create(self, sandbox_id: str, uri: str, schema: dict[str, Any]) -> dict[str, Any]:
        ctx = self._ctx(sandbox_id)
        self._refresh(ctx)
        ctx.permissions.require(Capability.CREATE)
        ctx.limiter.record_object()

        rewritten = rewrite_uri(ctx.sandbox_id, uri)
        forbidden = forbidden_root(uri)
        created = ctx.tools.qso_create(rewritten, schema)
        self._append_op(
            ctx,
            {
                "op": "create",
                "uri": rewritten,
                "schema": schema,
            },
        )
        return {
            "sandbox_id": sandbox_id,
            "uri": rewritten,
            "forbidden_root_rewrite": forbidden,
            "qso": created,
            "limits": ctx.limiter.snapshot(),
        }

    def read(self, sandbox_id: str, uri: str) -> dict[str, Any]:
        ctx = self._ctx(sandbox_id)
        self._refresh(ctx)
        ctx.permissions.require(Capability.READ)
        ctx.limiter.record_event()
        rewritten = rewrite_uri(ctx.sandbox_id, uri)
        return ctx.tools.qso_read(rewritten)

    def patch(self, sandbox_id: str, uri: str, delta: dict[str, Any], *, actor: str = "sandbox-agent") -> dict[str, Any]:
        ctx = self._ctx(sandbox_id)
        self._refresh(ctx)
        ctx.permissions.require(Capability.PATCH)
        ctx.limiter.record_event()
        rewritten = rewrite_uri(ctx.sandbox_id, uri)
        event = ctx.tools.qso_patch(rewritten, delta, actor=actor)
        self._append_op(
            ctx,
            {
                "op": "patch",
                "uri": rewritten,
                "delta": delta,
                "actor": actor,
            },
        )
        return event

    def timeline(self, sandbox_id: str, uri: str) -> list[dict[str, Any]]:
        ctx = self._ctx(sandbox_id)
        self._refresh(ctx)
        ctx.permissions.require(Capability.TIMELINE)
        ctx.limiter.record_event()
        rewritten = rewrite_uri(ctx.sandbox_id, uri)
        return ctx.tools.qso_timeline(rewritten)

    def entangle(self, sandbox_id: str, uri_a: str, uri_b: str, relationship: str) -> dict[str, Any]:
        ctx = self._ctx(sandbox_id)
        self._refresh(ctx)
        ctx.permissions.require(Capability.ENTANGLE)
        ctx.limiter.record_entanglement()
        a = rewrite_uri(ctx.sandbox_id, uri_a)
        b = rewrite_uri(ctx.sandbox_id, uri_b)
        ent = ctx.tools.qso_entangle(a, b, relationship)
        self._append_op(
            ctx,
            {
                "op": "entangle",
                "uri_a": a,
                "uri_b": b,
                "relationship": relationship,
            },
        )
        return ent

    def export_snapshot(self, sandbox_id: str, uri: str) -> dict[str, Any]:
        ctx = self._ctx(sandbox_id)
        self._refresh(ctx)
        ctx.permissions.require(Capability.EXPORT)
        ctx.limiter.record_event()
        rewritten = rewrite_uri(ctx.sandbox_id, uri)
        blob = ctx.tools.qso_export_snapshot(rewritten)
        encoded = base64.b64encode(blob).decode("ascii")
        return {
            "uri": rewritten,
            "snapshot_b64": encoded,
            "size_bytes": len(blob),
        }

    def subscribe(self, sandbox_id: str, uri: str) -> AsyncIterator[dict[str, Any]]:
        ctx = self._ctx(sandbox_id)
        self._refresh(ctx)
        ctx.permissions.require(Capability.SUBSCRIBE)
        rewritten = rewrite_uri(ctx.sandbox_id, uri)
        return ctx.tools.qso_subscribe(rewritten)

    def sandbox_status(self, sandbox_id: str) -> dict[str, Any]:
        ctx = self._ctx(sandbox_id)
        self._refresh(ctx)
        return {
            "sandbox_id": sandbox_id,
            "limits": ctx.limiter.snapshot(),
            "capabilities": sorted(cap.value for cap in ctx.permissions.capabilities),
            "persisted_ops": ctx.applied_ops,
        }

    def _ctx(self, sandbox_id: str) -> SandboxContext:
        if sandbox_id not in self._sandboxes:
            raise KeyError(f"sandbox not found: {sandbox_id}")
        return self._sandboxes[sandbox_id]

    def _append_op(self, ctx: SandboxContext, operation: dict[str, Any]) -> None:
        self.store.append_op(ctx.sandbox_id, operation)
        ctx.applied_ops += 1

    def _refresh(self, ctx: SandboxContext) -> None:
        operations = self.store.read_ops(ctx.sandbox_id)
        if ctx.applied_ops >= len(operations):
            return
        for operation in operations[ctx.applied_ops :]:
            self._replay_operation(ctx, operation)
        ctx.applied_ops = len(operations)

    def _replay_operation(self, ctx: SandboxContext, operation: dict[str, Any]) -> None:
        op = str(operation.get("op", ""))
        if op == "create":
            uri = str(operation["uri"])
            schema = operation.get("schema", {})
            try:
                ctx.tools.qso_create(uri, schema if isinstance(schema, dict) else {})
            except ValueError:
                # Already created in this runtime view.
                pass
            return
        if op == "patch":
            ctx.tools.qso_patch(
                str(operation["uri"]),
                dict(operation.get("delta", {})),
                actor=str(operation.get("actor", "sandbox-agent")),
            )
            return
        if op == "entangle":
            ctx.tools.qso_entangle(
                str(operation["uri_a"]),
                str(operation["uri_b"]),
                str(operation.get("relationship", "related")),
            )
            return
        raise ValueError(f"unknown sandbox operation: {op}")
