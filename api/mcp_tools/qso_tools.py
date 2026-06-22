from __future__ import annotations

import asyncio
import base64
import binascii
import json
from contextlib import suppress
from typing import Any, AsyncIterator, Dict

from api.schemas.models import EntanglementLink
from federation.checkpointing.hash_chain import checkpoint_hash
from qso_vr_visualization.interest_manager import InterestManager
from qso_vr_visualization.projection_compiler import ProjectionCompiler
from qso_vr_visualization.scene_render_projector import SceneRenderProjector
from services.runtime import QSOFabricRuntime
from services.transport.models import TransportRequest


class QSOMCPTools:
    """MCP tool surface for QSO state fabric runtime."""

    def __init__(self, runtime: QSOFabricRuntime | None = None) -> None:
        self.runtime = runtime or QSOFabricRuntime()
        self._scene_projector = SceneRenderProjector()
        self._scene_frame_by_world: Dict[str, int] = {}

    def qso_create(self, uri: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        obj = self.runtime.state_engine.create_object(uri=uri, schema=schema)
        return obj.model_dump(mode="json")

    def qso_read(self, uri: str) -> Dict[str, Any]:
        obj = self.runtime.state_engine.read(uri)
        return obj.model_dump(mode="json")

    def qso_patch(
        self,
        uri: str,
        delta: Dict[str, Any],
        actor: str = "agent",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        event = self.runtime.state_engine.patch(
            uri=uri,
            delta=delta,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        event_index = len(self.runtime.event_log.timeline(uri)) - 1
        payload = self._event_payload(
            uri=uri,
            event=event.model_dump(mode="json"),
            delta=delta,
            event_index=event_index,
            source="live",
        )
        self._dispatch_stream(uri, payload)
        timeline = [row.model_dump(mode="json") for row in self.runtime.event_log.timeline(uri)]
        self.runtime.checkpoint_store.put(uri, len(timeline), checkpoint_hash(timeline))
        return event.model_dump(mode="json")

    def qso_transport_status(self) -> Dict[str, Any]:
        return self.runtime.transport.status()

    def qso_transport_policy(self) -> Dict[str, Any]:
        return self.runtime.transport.policy()

    def qso_transport_health(self) -> Dict[str, Any]:
        return self.runtime.transport.health()

    def qso_transport_metrics(self) -> Dict[str, Any]:
        return self.runtime.transport.metrics()

    def qso_transport_set(
        self,
        mode: str,
        *,
        actor: str = "transport-controller",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        out = self.runtime.transport.set_mode(
            mode=mode,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        event = self._upsert_transport_qso(
            state_payload=dict(out["state"]),
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        return {
            **out,
            "qso_event": event.model_dump(mode="json"),
        }

    def qso_transport_send(
        self,
        *,
        workload_type: str,
        method: str,
        url: str,
        headers: Dict[str, Any] | None = None,
        body: str | bytes | None = None,
        actor: str = "transport-client",
        policy_version: str = "v1",
        node_id: str = "local",
        timeout_seconds: float = 10.0,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        request = TransportRequest.from_inputs(
            method=method,
            url=url,
            headers={str(k): str(v) for k, v in dict(headers or {}).items()},
            body=body,
            timeout_seconds=timeout_seconds,
            metadata=metadata or {},
        )
        out = self.runtime.transport.send(
            workload_type=workload_type,
            request=request,
            actor=actor,
            policy_version=policy_version,
        )
        event = self._upsert_transport_qso(
            state_payload=dict(out["state"]),
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        response = out["response"]
        return {
            "response": {
                "status_code": response.status_code,
                "headers": response.headers,
                "body_text": response.body_text(),
                "elapsed_ms": round(response.elapsed_ms, 6),
                "mode": response.mode.value,
                "adapter": response.adapter,
                "exit_fingerprint": response.exit_fingerprint,
                "error": response.error,
                "ok": response.ok,
            },
            "state": out["state"],
            "health": out["health"],
            "audit_event": out["audit_event"],
            "circuit_id": out["circuit_id"],
            "exit_profile": out["exit_profile"],
            "qso_event": event.model_dump(mode="json"),
        }

    def qso_subscribe(
        self,
        uri: str,
        cursor: int | str | None = None,
        backpressure: str = "block",
        queue_size: int = 512,
        strict: bool = True,
        include_replay: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        async def _stream() -> AsyncIterator[Dict[str, Any]]:
            subscriber = self.runtime.entanglement.register_subscriber(
                uri,
                queue_size=queue_size,
                backpressure=backpressure,
            )
            replay_cutoff: int | None = None

            def _live_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
                live_payload = dict(payload)
                event_uri = str(live_payload.get("uri", uri))
                event_index = live_payload.get("event_index")
                if "cursor_token" not in live_payload and isinstance(event_index, int) and event_index >= 0:
                    live_payload["cursor_token"] = self._single_cursor_token(event_uri, event_index + 1)
                live_payload["subscription"] = {"kind": "uri", "uri": uri}
                return live_payload

            try:
                if include_replay:
                    replayed = self.runtime.event_log.replay(uri, strict=strict)
                    start_index = 0
                    if cursor is not None:
                        start_index = self._resolve_single_cursor(uri=uri, cursor=cursor, replayed_len=len(replayed))
                    replay_cutoff = len(replayed)

                    for event_index, event in enumerate(replayed[start_index:], start=start_index):
                        replay_payload = self._event_payload(
                            uri=uri,
                            event=event.model_dump(mode="json"),
                            delta=event.delta,
                            event_index=event_index,
                            source="replay",
                        )
                        replay_payload["subscription"] = {"kind": "uri", "uri": uri}
                        yield replay_payload

                    while True:
                        try:
                            payload = subscriber.queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                        event_index = payload.get("event_index")
                        if isinstance(event_index, int) and event_index < replay_cutoff:
                            continue
                        yield _live_payload(payload)

                while True:
                    payload = await subscriber.queue.get()
                    if replay_cutoff is not None:
                        event_index = payload.get("event_index")
                        if isinstance(event_index, int) and event_index < replay_cutoff:
                            continue
                    yield _live_payload(payload)
            finally:
                self.runtime.entanglement.unregister_subscriber(uri, subscriber)

        return _stream()

    def qso_subscribe_prefix(
        self,
        uri_prefix: str,
        cursor: str | None = None,
        backpressure: str = "block",
        queue_size: int = 512,
        strict: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        uris = [uri for uri in self.runtime.registry.list_uris() if uri.startswith(uri_prefix)]
        next_by_uri = self._resolve_prefix_cursor(uri_prefix=uri_prefix, cursor=cursor, discovered_uris=uris)

        async def _stream() -> AsyncIterator[Dict[str, Any]]:
            replay_rows: list[tuple[str, str, str, str, int, Dict[str, Any]]] = []
            for current_uri in uris:
                events = self.runtime.event_log.replay(current_uri, strict=strict)
                start_index = next_by_uri.get(current_uri, 0)
                if start_index > len(events):
                    raise ValueError(f"cursor out of range for uri {current_uri}: {start_index} > {len(events)}")

                for event_index, event in enumerate(events[start_index:], start=start_index):
                    replay_rows.append(
                        (
                            event.timestamp.isoformat(),
                            event.event_id,
                            event.node_id,
                            current_uri,
                            event_index,
                            event.model_dump(mode="json"),
                        )
                    )

            replay_rows.sort(key=lambda row: (row[0], row[1], row[2], row[3], row[4]))

            for _, _, _, current_uri, event_index, event_payload in replay_rows:
                next_by_uri[current_uri] = event_index + 1
                payload = self._event_payload(
                    uri=current_uri,
                    event=event_payload,
                    delta=event_payload.get("delta", {}),
                    event_index=event_index,
                    source="replay",
                )
                payload["uri_cursor_token"] = payload["cursor_token"]
                payload["cursor_token"] = self._prefix_cursor_token(uri_prefix, next_by_uri)
                payload["subscription"] = {"kind": "prefix", "uri_prefix": uri_prefix}
                yield payload

            if not uris:
                return

            fan_in: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=max(1, queue_size))
            tasks: list[asyncio.Task[None]] = []

            async def _forward(source: AsyncIterator[Dict[str, Any]]) -> None:
                async for item in source:
                    await fan_in.put(item)

            for current_uri in uris:
                source = self.qso_subscribe(
                    current_uri,
                    cursor=None,
                    backpressure=backpressure,
                    queue_size=queue_size,
                    strict=strict,
                    include_replay=False,
                )
                tasks.append(asyncio.create_task(_forward(source)))

            try:
                while True:
                    payload = await fan_in.get()
                    merged = dict(payload)
                    event_uri = str(merged.get("uri", ""))
                    event_index = merged.get("event_index")
                    if event_uri and isinstance(event_index, int) and event_index >= 0:
                        next_by_uri[event_uri] = max(next_by_uri.get(event_uri, 0), event_index + 1)

                    if "cursor_token" in merged:
                        merged["uri_cursor_token"] = merged["cursor_token"]

                    merged["cursor_token"] = self._prefix_cursor_token(uri_prefix, next_by_uri)
                    merged["subscription"] = {"kind": "prefix", "uri_prefix": uri_prefix}
                    yield merged
            finally:
                for task in tasks:
                    task.cancel()
                for task in tasks:
                    with suppress(asyncio.CancelledError):
                        await task

        return _stream()

    def qso_subscribe_projection(
        self,
        uri: str,
        viewpoint: Dict[str, Any] | None = None,
        radius: float = 150.0,
        cursor: int | str | None = None,
        backpressure: str = "drop_oldest",
        queue_size: int = 256,
        strict: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        # Eagerly register a live subscriber so early patches aren't missed even if the
        # consumer starts iterating after the subscription is created (common in SSE).

        interest_manager = InterestManager(default_radius=radius)
        compiler = ProjectionCompiler()

        subscriber = self.runtime.entanglement.register_subscriber(
            uri,
            queue_size=queue_size,
            backpressure=backpressure,
        )

        async def _stream() -> AsyncIterator[Dict[str, Any]]:
            try:
                replayed = self.runtime.event_log.replay(uri, strict=strict)
                start_index = 0
                if cursor is not None:
                    start_index = self._resolve_single_cursor(uri=uri, cursor=cursor, replayed_len=len(replayed))
                replay_cutoff = len(replayed)

                for event_index, event in enumerate(replayed[start_index:], start=start_index):
                    payload = self._event_payload(
                        uri=uri,
                        event=event.model_dump(mode="json"),
                        delta=event.delta,
                        event_index=event_index,
                        source="replay",
                    )
                    payload["subscription"] = {"kind": "uri", "uri": uri}
                    proj = compiler.compile(payload, fallback_uri=uri)
                    proj_uri = str(proj.get("uri", uri)) if proj is not None else uri
                    if proj is not None and interest_manager.is_relevant(uri=proj_uri, projection=proj, viewpoint=viewpoint):
                        yield proj

                while True:
                    try:
                        payload = subscriber.queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    event_index = payload.get("event_index")
                    if isinstance(event_index, int) and event_index < replay_cutoff:
                        continue
                    proj = compiler.compile(dict(payload), fallback_uri=uri)
                    proj_uri = str(proj.get("uri", uri)) if proj is not None else uri
                    if proj is not None and interest_manager.is_relevant(uri=proj_uri, projection=proj, viewpoint=viewpoint):
                        yield proj

                while True:
                    payload = await subscriber.queue.get()
                    event_index = payload.get("event_index")
                    if isinstance(event_index, int) and event_index < replay_cutoff:
                        continue
                    proj = compiler.compile(dict(payload), fallback_uri=uri)
                    proj_uri = str(proj.get("uri", uri)) if proj is not None else uri
                    if proj is not None and interest_manager.is_relevant(uri=proj_uri, projection=proj, viewpoint=viewpoint):
                        yield proj
            finally:
                self.runtime.entanglement.unregister_subscriber(uri, subscriber)

        return _stream()

    def qso_scene_render_v1(
        self,
        world_uri: str,
        viewpoint: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        nodes = self._scene_nodes(world_uri)
        frame = self._next_scene_frame(world_uri)
        return self._scene_projector.project(
            world_uri=world_uri,
            nodes_by_uri=nodes,
            viewpoint=viewpoint,
            frame=frame,
        )

    def qso_subscribe_scene_render_v1(
        self,
        world_uri: str,
        *,
        viewpoint: Dict[str, Any] | None = None,
        cursor: str | None = None,
        backpressure: str = "drop_oldest",
        queue_size: int = 256,
        strict: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        world_uri = str(world_uri).rstrip("/")
        node_prefix = self._scene_node_prefix(world_uri)

        async def _stream() -> AsyncIterator[Dict[str, Any]]:
            effective_cursor = cursor
            if effective_cursor is None:
                effective_cursor = self._prefix_tail_cursor(uri_prefix=node_prefix, strict=strict)

            source = self.qso_subscribe_prefix(
                uri_prefix=node_prefix,
                cursor=effective_cursor,
                backpressure=backpressure,
                queue_size=queue_size,
                strict=strict,
            )
            fan_in: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=max(1, queue_size))

            async def _forward() -> None:
                async for event in source:
                    await fan_in.put(event)

            forward_task = asyncio.create_task(_forward())
            try:
                # Let the forwarder activate subscription plumbing before snapshot emit.
                await asyncio.sleep(0)

                snapshot = self.qso_scene_render_v1(world_uri=world_uri, viewpoint=viewpoint)
                snapshot["source"] = "snapshot"
                snapshot["subscription"] = {"kind": "scene_render_v1", "world_uri": world_uri}
                yield snapshot

                while True:
                    event = await fan_in.get()
                    proj = self.qso_scene_render_v1(world_uri=world_uri, viewpoint=viewpoint)
                    proj["source"] = str(event.get("source", "live"))
                    proj["changed_uri"] = str(event.get("uri", ""))
                    proj["cursor_token"] = event.get("cursor_token")
                    if "uri_cursor_token" in event:
                        proj["uri_cursor_token"] = event.get("uri_cursor_token")
                    proj["subscription"] = {"kind": "scene_render_v1", "world_uri": world_uri}
                    yield proj
            finally:
                forward_task.cancel()
                with suppress(asyncio.CancelledError):
                    await forward_task

        return _stream()

    def qso_scene_validate(self, world_uri: str) -> Dict[str, Any]:
        world_uri = str(world_uri).rstrip("/")
        nodes = self._scene_nodes(world_uri)
        return self._scene_projector.validate(world_uri=world_uri, nodes_by_uri=nodes)

    def qso_scene_reparent(
        self,
        *,
        node_uri: str,
        parent_uri: str | None,
        actor: str = "scene-author",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        node_uri = str(node_uri).strip()
        if not node_uri:
            raise ValueError("node_uri is required")
        if "/node/" not in node_uri:
            raise ValueError("node_uri must be a scene node URI containing '/node/'")

        new_parent = None
        if parent_uri is not None:
            parent_raw = str(parent_uri).strip()
            if parent_raw:
                new_parent = parent_raw

        world_uri = node_uri.split("/node/", 1)[0]
        nodes = self._scene_nodes(world_uri)
        if node_uri not in nodes:
            raise ValueError(f"node not found in world: {node_uri}")

        if new_parent is not None:
            if new_parent == node_uri:
                raise ValueError("node cannot be parent of itself")
            if new_parent not in nodes:
                raise ValueError(f"parent node not found in world: {new_parent}")
            if self._would_create_parent_cycle(node_uri=node_uri, parent_uri=new_parent, nodes=nodes):
                raise ValueError(f"reparent would create parent cycle: {node_uri} -> {new_parent}")

        event = self.qso_patch(
            uri=node_uri,
            delta={"parent": new_parent},
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        return {"event": event, "node": self.qso_read(node_uri)}

    def qso_export_snapshot(self, uri: str) -> bytes:
        obj = self.runtime.state_engine.read(uri)
        blob = self.runtime.snapshot_exporter.export_snapshot(
            uri=uri,
            state=obj.state_layer,
            entanglement=[link.model_dump(mode="json") for link in self.runtime.entanglement.list_links(uri)],
            event_count=len(self.runtime.event_log.timeline(uri)),
        )
        self.runtime.snapshot_store.put(uri, blob)
        return blob

    def qso_import_snapshot(self, qff: bytes) -> Dict[str, Any]:
        parsed = self.runtime.snapshot_exporter.import_snapshot(qff)
        uri = parsed["header"]["uri"]
        self.runtime.snapshot_store.put(uri, qff, label=f"import_{parsed['header'].get('event_count', 0)}")
        if not self.runtime.registry.has(uri):
            self.runtime.state_engine.create_object(uri=uri, schema={"imported": True})
        self.runtime.state_engine.patch(
            uri,
            parsed["state"],
            actor="snapshot-import",
            policy_version=str(parsed["header"].get("policy_version", "v1")),
            node_id="snapshot-import",
        )

        for raw_link in parsed["entanglement"]:
            self.runtime.entanglement.entangle(EntanglementLink(**raw_link), allow_cycle=False)
        return parsed

    def qso_entangle(
        self,
        uriA: str,
        uriB: str,
        relationship: str,
        strength: float = 1.0,
        sync_mode: str = "push",
        latency_target_ms: int = 100,
        bidirectional: bool = False,
        allow_cycle: bool = False,
    ) -> Dict[str, Any]:
        link = EntanglementLink(
            source_uri=uriA,
            target_uri=uriB,
            relationship=relationship,
            strength=strength,
            sync_mode=sync_mode,
            latency_target_ms=latency_target_ms,
            bidirectional=bidirectional,
        )
        self.runtime.entanglement.entangle(link, allow_cycle=allow_cycle)
        return link.model_dump(mode="json")

    def qso_timeline(self, uri: str, strict: bool = True) -> list[Dict[str, Any]]:
        return [event.model_dump(mode="json") for event in self.runtime.event_log.replay(uri, strict=strict)]

    def qso_publish_policy(self, policy: Dict[str, Any], actor: str = "gdml", node_id: str = "local") -> Dict[str, Any]:
        return self.runtime.gdml.policy_sync.publish(policy, actor=actor, node_id=node_id)

    def qso_policy_current(self) -> Dict[str, Any]:
        return self.runtime.gdml.policy_sync.current()

    def qso_quantum_create(
        self,
        uri: str,
        payload: Dict[str, Any],
        *,
        actor: str = "quantum-author",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        if not uri.startswith("qso://quantum."):
            raise ValueError("quantum uri must start with qso://quantum.")

        if not self.runtime.registry.has(uri):
            self.runtime.state_engine.create_object(
                uri=uri,
                schema={
                    "$id": "qso://quantum.network.object",
                    "type": "quantum_network_object",
                    "schema_ref": "api/schemas/quantum_network_object.schema.json",
                },
                actor=actor,
            )
        event = self.runtime.state_engine.patch(
            uri=uri,
            delta=dict(payload),
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        return {
            "uri": uri,
            "event": event.model_dump(mode="json"),
            "qso": self.qso_read(uri),
        }

    def qso_quantum_execute(
        self,
        uri: str,
        *,
        actor: str = "quantum-manager",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        return self.runtime.quantum.execute(
            uri=uri,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def qso_quantum_replay(self, uri: str, strict: bool = True) -> Dict[str, Any]:
        return self.runtime.quantum_replay.replay(uri, strict=strict)

    def qso_quantum_lisp_compile(self, source: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return self.runtime.quantum_lisp.compile(source, metadata=metadata or {})

    def qso_quantum_lisp_analyze(
        self,
        uri: str,
        *,
        actor: str = "quantum-lisp",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        return self.runtime.quantum_lisp.analyze(
            uri=uri,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def qso_quantum_lisp_replay(self, uri: str, strict: bool = True) -> Dict[str, Any]:
        return self.runtime.quantum_lisp.replay(uri=uri, strict=strict)

    def qso_quantum_qjfp_handshake(
        self,
        *,
        node_identity: str,
        hardware_signature: str,
        policy_version: str,
        quantum_capabilities: Dict[str, Any],
    ) -> Dict[str, Any]:
        accepted = bool(node_identity.strip() and hardware_signature.strip())
        reason = "accepted" if accepted else "missing_identity_or_signature"
        return {
            "accepted": accepted,
            "reason": reason,
            "node_identity": node_identity,
            "policy_version": policy_version,
            "quantum_capabilities": dict(quantum_capabilities),
        }

    def qso_identity_create(
        self,
        uri: str,
        immutable_core: Dict[str, Any],
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        event = self.runtime.state_engine.create_identity(
            uri=uri,
            immutable_core=immutable_core,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        return event.model_dump(mode="json")

    def qso_identity_event(
        self,
        uri: str,
        event_type: str,
        payload: Dict[str, Any],
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        event = self.runtime.state_engine.apply_identity_event(
            uri=uri,
            event_type=event_type,
            payload=payload,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        return event.model_dump(mode="json")

    def qso_identity_state(self, uri: str, strict: bool = True) -> Dict[str, Any]:
        return self.runtime.state_engine.rebuild_identity_state(uri, strict=strict)

    def qso_identity_authority_create(
        self,
        uri: str,
        immutable_core: Dict[str, Any],
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        event = self.runtime.identity_authority.create_identity(
            uri=uri,
            immutable_core=immutable_core,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        return event.model_dump(mode="json")

    def qso_identity_authority_issue_credential(
        self,
        uri: str,
        credential_id: str,
        credential_body: Dict[str, Any] | None = None,
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        event = self.runtime.identity_authority.issue_credential(
            uri=uri,
            credential_id=credential_id,
            credential_body=credential_body,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        return event.model_dump(mode="json")

    def qso_identity_authority_revoke_credential(
        self,
        uri: str,
        credential_id: str,
        reason: str,
        actor: str = "authority",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        event = self.runtime.identity_authority.revoke_credential(
            uri=uri,
            credential_id=credential_id,
            reason=reason,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        return event.model_dump(mode="json")

    def qso_identity_authority_publish_policy(
        self,
        policy: Dict[str, Any],
        actor: str = "authority",
        node_id: str = "local",
    ) -> Dict[str, Any]:
        return self.runtime.identity_authority.publish_policy(policy=policy, actor=actor, node_id=node_id)

    def qso_identity_authority_policy_current(self) -> Dict[str, Any]:
        return self.runtime.identity_authority.current_policy()

    def qso_identity_export_bundle(
        self,
        uri: str,
        trust_roots: list[str] | None = None,
        strict: bool = True,
    ) -> Dict[str, Any]:
        return self.runtime.identity_verifier.export_bundle(uri=uri, trust_roots=trust_roots, strict=strict)

    def qso_identity_bundle_sign(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        return self.runtime.identity_verifier.sign_bundle(bundle)

    def qso_identity_verify_bundle(
        self,
        bundle: Dict[str, Any],
        strict_archival: bool = True,
        reject_archived: bool = True,
    ) -> Dict[str, Any]:
        return self.runtime.identity_verifier.verify_bundle(
            bundle=bundle,
            strict_archival=strict_archival,
            reject_archived=reject_archived,
        )

    def qso_cursor_decode(self, token: str) -> Dict[str, Any]:
        return self._decode_cursor(token)

    def qso_cursor_encode_uri(self, uri: str, next_event_index: int) -> str:
        return self._single_cursor_token(uri, next_event_index)

    def qso_cursor_encode_prefix(self, uri_prefix: str, next_by_uri: Dict[str, int]) -> str:
        return self._prefix_cursor_token(uri_prefix, next_by_uri)

    def _dispatch_stream(self, source_uri: str, payload: Dict[str, Any]) -> None:
        async def _publish() -> None:
            await self.runtime.entanglement.publish_patch(source_uri, payload)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_publish())
        else:
            loop.create_task(_publish())

    def _event_payload(
        self,
        *,
        uri: str,
        event: Dict[str, Any],
        delta: Dict[str, Any],
        event_index: int,
        source: str,
    ) -> Dict[str, Any]:
        return {
            "uri": uri,
            "event": event,
            "delta": delta,
            "event_index": event_index,
            "source": source,
            "cursor_token": self._single_cursor_token(uri, event_index + 1),
        }

    def _resolve_single_cursor(self, uri: str, cursor: int | str, replayed_len: int) -> int:
        if isinstance(cursor, int):
            start_index = cursor
        elif isinstance(cursor, str):
            payload = self._decode_cursor(cursor)
            if payload.get("kind") != "uri":
                raise ValueError("cursor token kind mismatch, expected 'uri'")
            if payload.get("uri") != uri:
                raise ValueError(f"cursor token uri mismatch: {payload.get('uri')} != {uri}")
            start_index = payload.get("next_event_index")
            if not isinstance(start_index, int):
                raise ValueError("cursor token missing valid next_event_index")
        else:
            raise ValueError("cursor must be int, str token, or None")

        if start_index < 0:
            raise ValueError("cursor must be >= 0")
        if start_index > replayed_len:
            raise ValueError(f"cursor out of range for uri {uri}: {start_index} > {replayed_len}")
        return start_index

    def _resolve_prefix_cursor(
        self,
        uri_prefix: str,
        cursor: str | None,
        discovered_uris: list[str],
    ) -> Dict[str, int]:
        next_by_uri: Dict[str, int] = {uri: 0 for uri in discovered_uris}
        if cursor is None:
            return next_by_uri

        payload = self._decode_cursor(cursor)
        if payload.get("kind") != "prefix":
            raise ValueError("cursor token kind mismatch, expected 'prefix'")
        if payload.get("prefix") != uri_prefix:
            raise ValueError(f"cursor token prefix mismatch: {payload.get('prefix')} != {uri_prefix}")

        token_map = payload.get("next_by_uri")
        if not isinstance(token_map, dict):
            raise ValueError("prefix cursor token missing next_by_uri map")

        for uri, raw_index in token_map.items():
            if not isinstance(uri, str) or not uri.startswith(uri_prefix):
                raise ValueError(f"prefix cursor contains uri outside prefix: {uri}")
            if not isinstance(raw_index, int) or raw_index < 0:
                raise ValueError(f"prefix cursor has invalid event index for uri {uri}")
            next_by_uri[uri] = raw_index

        return next_by_uri

    @staticmethod
    def _scene_node_prefix(world_uri: str) -> str:
        return str(world_uri).rstrip("/") + "/node/"

    def _scene_nodes(self, world_uri: str) -> Dict[str, Dict[str, Any]]:
        prefix = self._scene_node_prefix(world_uri)
        nodes: Dict[str, Dict[str, Any]] = {}
        for uri in self.runtime.registry.list_uris():
            if not uri.startswith(prefix):
                continue
            obj = self.runtime.state_engine.read(uri)
            state = dict(obj.state_layer)
            if "id" not in state:
                state["id"] = uri.rsplit("/", 1)[-1]
            nodes[uri] = state
        return nodes

    def _upsert_transport_qso(
        self,
        *,
        state_payload: Dict[str, Any],
        actor: str,
        policy_version: str,
        node_id: str,
    ):
        uri = self.runtime.transport.OBJECT_URI
        if not self.runtime.registry.has(uri):
            self.runtime.state_engine.create_object(
                uri=uri,
                schema={
                    "$id": "qso://infra.transport",
                    "type": "transport",
                    "schema_ref": "api/schemas/transport.schema.json",
                },
                actor=actor,
            )
        return self.runtime.state_engine.patch(
            uri=uri,
            delta=dict(state_payload),
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )

    def _prefix_tail_cursor(self, *, uri_prefix: str, strict: bool) -> str:
        next_by_uri: Dict[str, int] = {}
        for uri in self.runtime.registry.list_uris():
            if not uri.startswith(uri_prefix):
                continue
            next_by_uri[uri] = len(self.runtime.event_log.replay(uri, strict=strict))
        return self._prefix_cursor_token(uri_prefix, next_by_uri)

    @staticmethod
    def _would_create_parent_cycle(
        *,
        node_uri: str,
        parent_uri: str,
        nodes: Dict[str, Dict[str, Any]],
    ) -> bool:
        cur: str | None = parent_uri
        seen: set[str] = set()
        while cur is not None and cur in nodes and cur not in seen:
            if cur == node_uri:
                return True
            seen.add(cur)
            nxt = nodes[cur].get("parent")
            if isinstance(nxt, str) and nxt.strip():
                cur = nxt.strip()
            else:
                cur = None
        return False

    def _next_scene_frame(self, world_uri: str) -> int:
        world = str(world_uri).rstrip("/")
        current = int(self._scene_frame_by_world.get(world, 0))
        nxt = current + 1
        self._scene_frame_by_world[world] = nxt
        return nxt

    @staticmethod
    def _single_cursor_token(uri: str, next_event_index: int) -> str:
        if next_event_index < 0:
            raise ValueError("next_event_index must be >= 0")
        return QSOMCPTools._encode_cursor(
            {
                "v": 1,
                "kind": "uri",
                "uri": uri,
                "next_event_index": next_event_index,
            }
        )

    @staticmethod
    def _prefix_cursor_token(uri_prefix: str, next_by_uri: Dict[str, int]) -> str:
        clean_map: Dict[str, int] = {}
        for uri, index in next_by_uri.items():
            if not isinstance(index, int) or index < 0:
                raise ValueError(f"invalid prefix cursor index for uri {uri}")
            clean_map[uri] = index
        return QSOMCPTools._encode_cursor(
            {
                "v": 1,
                "kind": "prefix",
                "prefix": uri_prefix,
                "next_by_uri": clean_map,
            }
        )

    @staticmethod
    def _encode_cursor(payload: Dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(token: str) -> Dict[str, Any]:
        if not token:
            raise ValueError("cursor token must be non-empty")

        padding = "=" * (-len(token) % 4)
        try:
            raw = base64.urlsafe_b64decode(token + padding)
        except binascii.Error as exc:
            raise ValueError("invalid cursor token encoding") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid cursor token payload") from exc

        if not isinstance(payload, dict):
            raise ValueError("cursor token payload must be an object")
        if payload.get("v") != 1:
            raise ValueError(f"unsupported cursor token version: {payload.get('v')}")
        return payload
