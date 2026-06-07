from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import parse_qs, urlparse

from api.mcp_tools.qso_tools import QSOMCPTools
from federation.handshake.policy_handshake import compatible
from services.plugins.nlm_client import (
    NLMDigitalCollectionsClient,
    NLMDigitalCollectionsClientError,
    NLMDigitalCollectionsRateLimitError,
)
from services.plugins.service import PluginService
from solis.config import SolisConfig
from solis.governance.rbac import RBACAuthorizer, RBACDecision
from snapshot.validation.compatibility import snapshot_compatible


def _state_digest(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _identity_uri(identity_id: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", identity_id).strip("_")
    if not slug:
        raise ValueError("identity_id must contain at least one valid character")
    return f"qso://identity.person.{slug}"


def _as_dict(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("request body must be a JSON object")
    return value


def _plugin_ids(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
        return parts or None
    if isinstance(value, list):
        parts = [str(part).strip() for part in value if str(part).strip()]
        return parts or None
    raise ValueError("plugin_ids must be a list or a comma-separated string")


class QSOIdentityRESTAPI:
    """Transport adapter for identity/federation endpoints over plain HTTP JSON."""

    def __init__(
        self,
        tools: QSOMCPTools | None = None,
        runtime_version: str = "qso-fabric/0.1.0",
        required_api_token: str | None = None,
        require_signed_fields: bool = True,
        verify_request_signatures: bool | None = None,
        max_request_bytes: int | None = None,
        enforce_rbac: bool | None = None,
        rbac_authorizer: RBACAuthorizer | None = None,
        default_rbac_role: str = "operator",
    ) -> None:
        self.tools = tools or QSOMCPTools()
        self.runtime_version = runtime_version
        env_token = os.getenv("QSO_API_TOKEN", "").strip()
        self.required_api_token = (required_api_token if required_api_token is not None else env_token).strip()
        self.require_signed_fields = require_signed_fields
        max_request_raw = str(os.getenv("QSO_HTTP_MAX_REQUEST_BYTES", "")).strip()
        if max_request_bytes is None:
            try:
                max_request_bytes = int(max_request_raw) if max_request_raw else 1_048_576
            except ValueError:
                max_request_bytes = 1_048_576
        self.max_request_bytes = max(4096, int(max_request_bytes))
        if verify_request_signatures is None:
            raw = os.getenv("QSO_VERIFY_REQUEST_SIGNATURES", "0").strip().lower()
            verify_request_signatures = raw in {"1", "true", "yes", "on"}
        self.verify_request_signatures = bool(verify_request_signatures)
        if enforce_rbac is None:
            raw_rbac = os.getenv("QSO_ENFORCE_RBAC", "0").strip().lower()
            enforce_rbac = raw_rbac in {"1", "true", "yes", "on"}
        self.enforce_rbac = bool(enforce_rbac)
        self.rbac_authorizer = rbac_authorizer or RBACAuthorizer()
        self.default_rbac_role = default_rbac_role.strip().lower() or "operator"
        self.solis_config = SolisConfig()
        self._rbac_audit_counter = 0
        self._rbac_decision_uris: list[str] = []
        self.plugins = getattr(self.tools.runtime, "plugins", PluginService())
        self.nlm_client = NLMDigitalCollectionsClient(
            tool=str(os.getenv("QSO_NLM_TOOL", "qso_fabric_demo")).strip() or "qso_fabric_demo",
            email=str(os.getenv("QSO_NLM_EMAIL", "")).strip() or None,
        )

    def route_post(self, path: str, body: Dict[str, Any], headers: Dict[str, str] | None = None) -> Tuple[int, Dict[str, Any]]:
        routes = {
            "/v1/qso/create": self._qso_create,
            "/v1/qso/patch": self._qso_patch,
            "/v1/transport/set": self._transport_set,
            "/v1/transport/send": self._transport_send,
            "/v1/qso/scene/reparent": self._qso_scene_reparent,
            "/v1/demo/plugins/apply": self._demo_plugins_apply,
            "/v1/demo/plugins/nlm/search": self._demo_nlm_search,
            "/v1/demo/plugins/nlm/search/continue": self._demo_nlm_continue,
            "/v1/identity/create": self._create_identity,
            "/v1/identity/mutate": self._mutate_identity,
            "/v1/identity/revoke": self._revoke_identity,
            "/v1/identity/reinstate": self._reinstate_identity,
            "/v1/policy/propose": self._propose_policy,
            "/v1/policy/activate": self._activate_policy,
            "/v1/federation/handshake": self._federation_handshake,
            "/v1/archive/export": self._archive_export,
            "/v1/archive/import": self._archive_import,
        }
        handler = routes.get(path)
        if handler is None:
            return HTTPStatus.NOT_FOUND, {"error": f"unknown route: {path}"}
        try:
            auth = self._authorize(path=path, headers=headers or {})
            if auth is not None:
                return auth
            payload = _as_dict(body)
            rbac = self._authorize_rbac(method="POST", path=path, body=payload, headers=headers or {})
            if rbac is not None:
                return rbac
            signed_check = self._validate_signed_request(path=path, body=payload)
            if signed_check is not None:
                return signed_check
            return handler(payload)
        except NLMDigitalCollectionsRateLimitError as exc:
            return HTTPStatus.TOO_MANY_REQUESTS, {"error": str(exc)}
        except NLMDigitalCollectionsClientError as exc:
            return HTTPStatus.BAD_GATEWAY, {"error": str(exc)}
        except KeyError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": f"missing required field: {exc.args[0]}"}
        except ValueError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": str(exc)}

    def route_get(
        self,
        path: str,
        query: Dict[str, str] | None = None,
        headers: Dict[str, str] | None = None,
    ) -> Tuple[int, Dict[str, Any]]:
        try:
            auth = self._authorize(path=path, headers=headers or {})
            if auth is not None:
                return auth
            query_map = query or {}
            rbac = self._authorize_rbac(method="GET", path=path, body=None, headers=headers or {})
            if rbac is not None:
                return rbac
            if path == "/healthz":
                return HTTPStatus.OK, {"ok": True, "runtime_version": self.runtime_version}
            if path == "/readyz":
                report = self.tools.runtime.health_report()
                report["runtime_version"] = self.runtime_version
                return (HTTPStatus.OK if bool(report.get("ok")) else HTTPStatus.SERVICE_UNAVAILABLE), report
            if path == "/v1/qso/read":
                return self._qso_read(query_map)
            if path == "/v1/transport/status":
                return self._transport_status()
            if path == "/v1/transport/health":
                return self._transport_health()
            if path == "/v1/transport/policy":
                return self._transport_policy()
            if path == "/v1/qso/scene/render_v1":
                return self._qso_scene_render_v1(query_map)
            if path == "/v1/qso/scene/validate":
                return self._qso_scene_validate(query_map)
            if path == "/v1/demo/plugins":
                return self._demo_plugins(query_map)
            if path == "/v1/policy/current":
                return HTTPStatus.OK, self.tools.qso_policy_current()
            return HTTPStatus.NOT_FOUND, {"error": f"unknown route: {path}"}
        except KeyError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": f"missing required field: {exc.args[0]}"}
        except ValueError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": str(exc)}

    def _event_response(self, event_id: str, object_uri: str, state_hash: str) -> Tuple[int, Dict[str, Any]]:
        return HTTPStatus.OK, {
            "event_id": event_id,
            "state_hash": state_hash,
            "object_uri": object_uri,
        }

    def _create_identity(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        identity_id = str(body["identity_id"])
        uri = _identity_uri(identity_id)
        event = self.tools.qso_identity_authority_create(
            uri=uri,
            immutable_core=deepcopy(dict(body["immutable_core"])),
            actor=str(body.get("actor", "authority")),
            policy_version=str(body.get("policy_version", "v1")),
            node_id=str(body.get("node_id", "rest")),
        )
        state = self.tools.qso_identity_state(uri, strict=True)
        return self._event_response(event_id=str(event["event_id"]), object_uri=uri, state_hash=str(state["state_hash"]))

    def _qso_create(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        uri = str(body["uri"])
        schema = deepcopy(dict(body.get("schema", {"type": "object"})))
        self.tools.qso_create(uri=uri, schema=schema)

        raw_state = body.get("state", {})
        if raw_state is None:
            raw_state = {}
        if not isinstance(raw_state, dict):
            raise ValueError("state must be an object when provided")

        if raw_state:
            self.tools.qso_patch(
                uri=uri,
                delta=deepcopy(raw_state),
                actor=str(body.get("actor", "scene-author")),
                policy_version=str(body.get("policy_version", "v1")),
                node_id=str(body.get("node_id", "rest")),
            )
        return HTTPStatus.OK, self.tools.qso_read(uri)

    def _qso_patch(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        uri = str(body["uri"])
        delta = deepcopy(dict(body["delta"]))
        event = self.tools.qso_patch(
            uri=uri,
            delta=delta,
            actor=str(body.get("actor", "scene-author")),
            policy_version=str(body.get("policy_version", "v1")),
            node_id=str(body.get("node_id", "rest")),
        )
        return HTTPStatus.OK, event

    def _transport_set(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        out = self.tools.qso_transport_set(
            mode=str(body["mode"]),
            actor=str(body.get("actor", "transport-rest")),
            policy_version=str(body.get("policy_version", "v1")),
            node_id=str(body.get("node_id", "rest")),
        )
        return HTTPStatus.OK, out

    def _transport_send(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        out = self.tools.qso_transport_send(
            workload_type=str(body.get("workload_type", "research")),
            method=str(body.get("method", "GET")),
            url=str(body["url"]),
            headers=(deepcopy(dict(body.get("headers", {}))) if isinstance(body.get("headers", {}), dict) else {}),
            body=(body.get("body") if isinstance(body.get("body"), (str, bytes)) else None),
            actor=str(body.get("actor", "transport-rest")),
            policy_version=str(body.get("policy_version", "v1")),
            node_id=str(body.get("node_id", "rest")),
            timeout_seconds=float(body.get("timeout_seconds", 10.0)),
            metadata=(deepcopy(dict(body.get("metadata", {}))) if isinstance(body.get("metadata", {}), dict) else {}),
        )
        return HTTPStatus.OK, out

    def _qso_scene_reparent(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        node_uri = str(body["node_uri"])
        raw_parent = body.get("parent_uri")
        parent_uri = None if raw_parent is None else str(raw_parent)
        out = self.tools.qso_scene_reparent(
            node_uri=node_uri,
            parent_uri=parent_uri,
            actor=str(body.get("actor", "scene-author")),
            policy_version=str(body.get("policy_version", "v1")),
            node_id=str(body.get("node_id", "rest")),
        )
        return HTTPStatus.OK, out

    def _qso_read(self, query: Dict[str, str]) -> Tuple[int, Dict[str, Any]]:
        uri = str(query.get("uri", "")).strip()
        if not uri:
            raise ValueError("uri query parameter is required")
        return HTTPStatus.OK, self.tools.qso_read(uri)

    def _transport_status(self) -> Tuple[int, Dict[str, Any]]:
        return HTTPStatus.OK, self.tools.qso_transport_status()

    def _transport_health(self) -> Tuple[int, Dict[str, Any]]:
        return HTTPStatus.OK, self.tools.qso_transport_health()

    def _transport_policy(self) -> Tuple[int, Dict[str, Any]]:
        return HTTPStatus.OK, self.tools.qso_transport_policy()

    def _qso_scene_render_v1(self, query: Dict[str, str]) -> Tuple[int, Dict[str, Any]]:
        world_uri = str(query.get("world_uri", "")).strip()
        if not world_uri:
            raise ValueError("world_uri query parameter is required")

        viewpoint: Dict[str, Any] = {}
        raw_viewpoint = str(query.get("viewpoint", "")).strip()
        if raw_viewpoint:
            parsed = json.loads(raw_viewpoint)
            if not isinstance(parsed, dict):
                raise ValueError("viewpoint must be a JSON object")
            viewpoint = parsed

        projection = self.tools.qso_scene_render_v1(world_uri=world_uri, viewpoint=viewpoint or None)
        return HTTPStatus.OK, projection

    def _qso_scene_validate(self, query: Dict[str, str]) -> Tuple[int, Dict[str, Any]]:
        world_uri = str(query.get("world_uri", "")).strip()
        if not world_uri:
            raise ValueError("world_uri query parameter is required")
        return HTTPStatus.OK, self.tools.qso_scene_validate(world_uri=world_uri)

    def _demo_plugins(self, query: Dict[str, str]) -> Tuple[int, Dict[str, Any]]:
        world_uri = str(query.get("world_uri", "qso://vr.world/demo")).strip()
        if not world_uri:
            world_uri = "qso://vr.world/demo"
        plugin_ids = _plugin_ids(query.get("plugin_ids"))
        return HTTPStatus.OK, self.plugins.demo_payload(world_uri=world_uri, plugin_ids=plugin_ids)

    def _demo_plugins_apply(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        world_uri = str(body.get("world_uri", "qso://vr.world/demo")).strip()
        if not world_uri:
            world_uri = "qso://vr.world/demo"
        plugin_ids = _plugin_ids(body.get("plugin_ids"))
        out = self.plugins.apply_demo_plugins(
            tools=self.tools,
            world_uri=world_uri,
            actor=str(body.get("actor", "scene-plugin")),
            policy_version=str(body.get("policy_version", "v1")),
            node_id=str(body.get("node_id", "rest")),
            plugin_ids=plugin_ids,
        )
        return HTTPStatus.OK, out

    def _demo_nlm_search(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        term = str(body["term"]).strip()
        if not term:
            raise ValueError("term must not be empty")
        cache_ttl_raw = body.get("cache_ttl_seconds")
        cache_ttl_seconds = None if cache_ttl_raw is None else int(str(cache_ttl_raw))
        payload = self.nlm_client.search(
            term=term,
            retmax=int(body.get("retmax", 10)),
            tool=(None if body.get("tool") is None else str(body.get("tool"))),
            email=(None if body.get("email") is None else str(body.get("email"))),
            use_cache=bool(body.get("use_cache", True)),
            cache_ttl_seconds=cache_ttl_seconds,
        )
        return HTTPStatus.OK, payload

    def _demo_nlm_continue(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        cache_ttl_raw = body.get("cache_ttl_seconds")
        cache_ttl_seconds = None if cache_ttl_raw is None else int(str(cache_ttl_raw))
        payload = self.nlm_client.continue_search(
            file=str(body["file"]),
            server=str(body["server"]),
            retstart=int(body["retstart"]),
            retmax=int(body.get("retmax", 10)),
            tool=(None if body.get("tool") is None else str(body.get("tool"))),
            email=(None if body.get("email") is None else str(body.get("email"))),
            use_cache=bool(body.get("use_cache", True)),
            cache_ttl_seconds=cache_ttl_seconds,
        )
        return HTTPStatus.OK, payload

    def _mutate_identity(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        identity_id = str(body["identity_id"])
        uri = _identity_uri(identity_id)

        event_type = str(body.get("event_type", "MEASURE_VERIFY"))
        if "payload" in body:
            payload = deepcopy(dict(body["payload"]))
        else:
            delta = deepcopy(dict(body.get("delta", {})))
            payload = {
                "measurement_id": f"mut_{uuid.uuid4().hex}",
                "result": True,
                "delta": delta,
            }
        if event_type == "MEASURE_VERIFY" and "measurement_id" not in payload:
            payload["measurement_id"] = f"measure_{uuid.uuid4().hex}"

        event = self.tools.qso_identity_event(
            uri=uri,
            event_type=event_type,
            payload=payload,
            actor=str(body.get("actor", "authority")),
            policy_version=str(body.get("policy_version", "v1")),
            node_id=str(body.get("node_id", "rest")),
        )
        state = self.tools.qso_identity_state(uri, strict=False)
        return self._event_response(event_id=str(event["event_id"]), object_uri=uri, state_hash=str(state["state_hash"]))

    def _revoke_identity(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        identity_id = str(body["identity_id"])
        uri = _identity_uri(identity_id)
        event = self.tools.qso_identity_event(
            uri=uri,
            event_type="IDENTITY_FREEZE",
            payload={"reason": str(body["reason"])},
            actor=str(body.get("actor", "authority")),
            policy_version=str(body.get("policy_version", "v1")),
            node_id=str(body.get("node_id", "rest")),
        )
        state = self.tools.qso_identity_state(uri, strict=False)
        return self._event_response(event_id=str(event["event_id"]), object_uri=uri, state_hash=str(state["state_hash"]))

    def _reinstate_identity(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        identity_id = str(body["identity_id"])
        uri = _identity_uri(identity_id)
        actor = str(body.get("actor", "authority"))
        policy_version = str(body.get("policy_version", "v1"))
        node_id = str(body.get("node_id", "rest"))

        marker = {
            "identity_reinstate": {
                "requested_by": actor,
                "requested_at": datetime.now(timezone.utc).isoformat(),
            }
        }
        event = self.tools.qso_patch(
            uri=uri,
            delta=marker,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        obj = self.tools.qso_read(uri)
        state_hash = _state_digest(obj.get("state_layer", {}))
        return self._event_response(event_id=str(event["event_id"]), object_uri=uri, state_hash=state_hash)

    def _propose_policy(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        policy = deepcopy(dict(body["policy_body"]))
        version = str(body["version"])
        policy["version"] = version
        updated = self.tools.qso_publish_policy(
            policy=policy,
            actor=str(body.get("actor", "governance")),
            node_id=str(body.get("node_id", "rest")),
        )
        event_id = f"policy_propose:{version}"
        return self._event_response(event_id=event_id, object_uri=str(body["policy_uri"]), state_hash=_state_digest(updated))

    def _activate_policy(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        policy = self.tools.qso_policy_current()
        requested_version = str(body["version"])
        if str(policy.get("version", "")) != requested_version:
            # Keep activation deterministic: publish the same policy with requested version.
            policy = {**policy, "version": requested_version}
            policy = self.tools.qso_publish_policy(
                policy=policy,
                actor=str(body.get("actor", "governance")),
                node_id=str(body.get("node_id", "rest")),
            )
        event_id = f"policy_activate:{requested_version}:{int(body['activation_index'])}"
        return self._event_response(event_id=event_id, object_uri=str(body["policy_uri"]), state_hash=_state_digest(policy))

    def _federation_handshake(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        runtime_ok = compatible(self.runtime_version, str(body["runtime_version"]))
        if not runtime_ok:
            return HTTPStatus.OK, {"accepted": False, "reason": "runtime_version_mismatch"}
        return HTTPStatus.OK, {"accepted": True, "reason": "ok"}

    def _archive_export(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        identity_id = str(body.get("identity_id", "")).strip()
        if identity_id:
            uri = _identity_uri(identity_id)
        else:
            uri = str(body["uri"])
        bundle = self.tools.qso_identity_export_bundle(
            uri=uri,
            trust_roots=body.get("trust_roots"),
            strict=bool(body.get("strict", True)),
        )
        return HTTPStatus.OK, {"accepted": True, "bundle": bundle}

    def _archive_import(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        bundle = deepcopy(dict(body["bundle"]))
        if "identity_snapshot_qff_b64" not in bundle and "identity_snapshot_qff" in bundle:
            header = bundle.get("header", {})
            runtime_version = str(header.get("runtime_version", self.runtime_version))
            if not snapshot_compatible(header, runtime_version):
                return HTTPStatus.OK, {"accepted": False, "reason": "snapshot_runtime_incompatible"}
        result = self.tools.qso_identity_verify_bundle(
            bundle=bundle,
            strict_archival=bool(body.get("strict_archival", True)),
            reject_archived=bool(body.get("reject_archived", True)),
        )
        if result.get("accepted"):
            return HTTPStatus.OK, {"accepted": True, "reason": "verification_passed"}
        return HTTPStatus.OK, {"accepted": False, "reason": str(result.get("reason", "verification_failed"))}

    def _authorize(self, path: str, headers: Dict[str, str]) -> Tuple[int, Dict[str, Any]] | None:
        if path in {"/healthz", "/readyz"}:
            return None

        if self.required_api_token:
            auth_header = headers.get("Authorization") or headers.get("authorization", "")
            prefix = "Bearer "
            if not auth_header.startswith(prefix):
                return HTTPStatus.UNAUTHORIZED, {"error": "missing bearer token"}
            token = auth_header[len(prefix) :].strip()
            if token != self.required_api_token:
                return HTTPStatus.UNAUTHORIZED, {"error": "invalid bearer token"}
        return None

    def _authorize_rbac(
        self,
        *,
        method: str,
        path: str,
        body: Dict[str, Any] | None,
        headers: Dict[str, str],
    ) -> Tuple[int, Dict[str, Any]] | None:
        if not self.enforce_rbac:
            return None

        action = self._resolve_rbac_action(method=method, path=path)
        if action is None:
            return None

        actor = self._resolve_rbac_actor(body=body, headers=headers)
        explicit_role = self._resolve_rbac_role(body=body, headers=headers)
        decision = self.rbac_authorizer.authorize(
            action=action,
            actor=actor,
            explicit_role=explicit_role,
            default_role=self.default_rbac_role,
        )
        audit_uri = self._emit_rbac_audit(
            method=method,
            path=path,
            actor=actor,
            decision=decision,
        )
        if not decision.allowed:
            return HTTPStatus.FORBIDDEN, {
                "error": "rbac_denied",
                "action": action,
                "role": decision.role,
                "reason": decision.reason_code,
                "audit_uri": audit_uri,
            }
        return None

    def _resolve_rbac_action(self, *, method: str, path: str) -> str | None:
        post_actions = {
            "/v1/qso/create": "execution.operate",
            "/v1/qso/patch": "execution.operate",
            "/v1/qso/scene/reparent": "execution.operate",
            "/v1/demo/plugins/apply": "execution.operate",
            "/v1/demo/plugins/nlm/search": "execution.operate",
            "/v1/demo/plugins/nlm/search/continue": "execution.operate",
            "/v1/identity/create": "identity.mutate",
            "/v1/identity/mutate": "identity.mutate",
            "/v1/identity/revoke": "identity.mutate",
            "/v1/identity/reinstate": "identity.mutate",
            "/v1/policy/propose": "policy.propose",
            "/v1/policy/activate": "policy.activate",
            "/v1/federation/handshake": "execution.operate",
            "/v1/archive/export": "archive.operate",
            "/v1/archive/import": "archive.operate",
        }
        get_actions = {
            "/healthz": None,
            "/readyz": None,
            "/v1/qso/read": "execution.read",
            "/v1/qso/scene/render_v1": "execution.read",
            "/v1/qso/scene/validate": "execution.read",
            "/v1/demo/plugins": "execution.read",
            "/v1/policy/current": "policy.read",
        }
        if method.upper() == "POST":
            return post_actions.get(path)
        if method.upper() == "GET":
            return get_actions.get(path)
        return None

    @staticmethod
    def _resolve_rbac_actor(body: Dict[str, Any] | None, headers: Dict[str, str]) -> str:
        if body is not None:
            actor = str(body.get("actor", "")).strip()
            if actor:
                return actor
        header_actor = str(headers.get("X-QSO-Actor") or headers.get("x-qso-actor") or "").strip()
        if header_actor:
            return header_actor
        return "operator://rest"

    @staticmethod
    def _resolve_rbac_role(body: Dict[str, Any] | None, headers: Dict[str, str]) -> str | None:
        if body is not None:
            role = str(body.get("role", "")).strip()
            if role:
                return role
        header_role = str(headers.get("X-QSO-Role") or headers.get("x-qso-role") or "").strip()
        return header_role or None

    def _emit_rbac_audit(self, *, method: str, path: str, actor: str, decision: RBACDecision) -> str:
        self._rbac_audit_counter += 1
        request_id = f"rbac-{self._rbac_audit_counter:08d}"
        action_slug = re.sub(r"[^A-Za-z0-9._-]+", "_", decision.action).strip("_") or "action"
        digest_input = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "action": decision.action,
            "actor": actor,
            "role": decision.role,
            "allowed": decision.allowed,
            "reason_code": decision.reason_code,
        }
        decision_id = hashlib.sha256(
            json.dumps(digest_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:24]
        uri = f"qso://solis.rbac.{action_slug}.{decision_id}"

        if not self.tools.runtime.registry.has(uri):
            self.tools.qso_create(uri, {"type": "solis_rbac_decision"})

        self.tools.qso_patch(
            uri=uri,
            delta={
                "request_id": request_id,
                "method": method,
                "path": path,
                "action": decision.action,
                "actor": actor,
                "role": decision.role,
                "allowed": decision.allowed,
                "reason_code": decision.reason_code,
            },
            actor="solis.rbac",
            policy_version=self.solis_config.policy_version,
            node_id="rest",
        )
        self._rbac_decision_uris.append(uri)
        return uri

    def _validate_signed_request(self, path: str, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]] | None:
        if not self.require_signed_fields:
            return None

        signed_paths = {
            "/v1/identity/create",
            "/v1/identity/mutate",
            "/v1/identity/revoke",
            "/v1/identity/reinstate",
            "/v1/policy/propose",
            "/v1/policy/activate",
        }
        if path not in signed_paths:
            return None

        for field in ("actor", "policy_version", "signature"):
            if field not in body or not str(body.get(field, "")).strip():
                return HTTPStatus.UNAUTHORIZED, {"error": f"missing signed field: {field}"}

        if not self.verify_request_signatures:
            return None

        signature = str(body["signature"])
        payload = {k: deepcopy(v) for k, v in body.items() if k != "signature"}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        valid = self.tools.runtime.crypto.verify(canonical, signature)
        if not valid:
            return HTTPStatus.UNAUTHORIZED, {"error": "invalid request signature"}
        return None


def make_http_handler(api: QSOIdentityRESTAPI) -> type[BaseHTTPRequestHandler]:
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/demo/three-webxr-scene-qso":
                self._write_demo_page()
                return
            query = {k: values[-1] for k, values in parse_qs(parsed.query, keep_blank_values=True).items()}
            status, payload = api.route_get(parsed.path, query=query, headers=dict(self.headers.items()))
            self._write_json(status, payload)

        def do_POST(self) -> None:  # noqa: N802
            try:
                content_len = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                content_len = 0
            if content_len > api.max_request_bytes:
                self._write_json(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    {
                        "error": f"request body too large ({content_len} bytes > {api.max_request_bytes} bytes)",
                    },
                )
                return
            raw = self.rfile.read(content_len) if content_len > 0 else b"{}"
            try:
                body = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON body"})
                return
            status, payload = api.route_post(urlparse(self.path).path, body, headers=dict(self.headers.items()))
            self._write_json(status, payload)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            # Keep CLI output clean by default.
            _ = (format, args)

        def _write_json(self, status: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _write_demo_page(self) -> None:
            demo_path = Path(__file__).resolve().parents[2] / "demo" / "three_webxr_scene_qso.html"
            if not demo_path.exists():
                self._write_json(HTTPStatus.NOT_FOUND, {"error": "demo page not found"})
                return

            body = demo_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return _Handler


def create_http_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    api: QSOIdentityRESTAPI | None = None,
) -> ThreadingHTTPServer:
    rest_api = api or QSOIdentityRESTAPI()
    return ThreadingHTTPServer((host, port), make_http_handler(rest_api))


def serve_http(host: str = "0.0.0.0", port: int = 8000, api: QSOIdentityRESTAPI | None = None) -> None:
    server = create_http_server(host=host, port=port, api=api)
    try:
        server.serve_forever()
    finally:
        server.server_close()
