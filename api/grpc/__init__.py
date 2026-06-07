from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict

from api.mcp_tools.qso_tools import QSOMCPTools
from api.rest import _identity_uri
from federation.handshake.policy_handshake import compatible


def _digest(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class QSOIdentityService:
    """In-process gRPC-style adapter matching qso_identity.proto semantics."""

    def __init__(self, tools: QSOMCPTools | None = None) -> None:
        self.tools = tools or QSOMCPTools()

    def CreateIdentity(self, request: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N802
        auth = dict(request.get("auth", {}))
        uri = _identity_uri(str(request["identity_id"]))
        event = self.tools.qso_identity_authority_create(
            uri=uri,
            immutable_core=deepcopy(dict(request.get("immutable_core", {}))),
            actor=str(auth.get("actor", "authority")),
            policy_version=str(auth.get("policy_version", "v1")),
            node_id=str(request.get("node_id", "grpc")),
        )
        state = self.tools.qso_identity_state(uri, strict=True)
        return {"event_id": event["event_id"], "state_hash": state["state_hash"], "object_uri": uri}

    def MutateIdentity(self, request: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N802
        auth = dict(request.get("auth", {}))
        uri = _identity_uri(str(request["identity_id"]))
        payload = {"measurement_id": f"grpc_{request.get('identity_id')}", "result": True, "delta": request.get("delta", {})}
        event = self.tools.qso_identity_event(
            uri=uri,
            event_type="MEASURE_VERIFY",
            payload=payload,
            actor=str(auth.get("actor", "authority")),
            policy_version=str(auth.get("policy_version", "v1")),
            node_id=str(request.get("node_id", "grpc")),
        )
        state = self.tools.qso_identity_state(uri, strict=False)
        return {"event_id": event["event_id"], "state_hash": state["state_hash"], "object_uri": uri}

    def RevokeIdentity(self, request: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N802
        auth = dict(request.get("auth", {}))
        uri = _identity_uri(str(request["identity_id"]))
        event = self.tools.qso_identity_event(
            uri=uri,
            event_type="IDENTITY_FREEZE",
            payload={"reason": str(request["reason"])},
            actor=str(auth.get("actor", "authority")),
            policy_version=str(auth.get("policy_version", "v1")),
            node_id=str(request.get("node_id", "grpc")),
        )
        state = self.tools.qso_identity_state(uri, strict=False)
        return {"event_id": event["event_id"], "state_hash": state["state_hash"], "object_uri": uri}

    def ReinstateIdentity(self, request: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N802
        auth = dict(request.get("auth", {}))
        uri = _identity_uri(str(request["identity_id"]))
        event = self.tools.qso_patch(
            uri=uri,
            delta={"identity_reinstate": {"source": "grpc"}},
            actor=str(auth.get("actor", "authority")),
            policy_version=str(auth.get("policy_version", "v1")),
            node_id=str(request.get("node_id", "grpc")),
        )
        state = self.tools.qso_read(uri)
        return {
            "event_id": event["event_id"],
            "state_hash": _digest(state.get("state_layer", {})),
            "object_uri": uri,
        }

    def ProposePolicy(self, request: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N802
        auth = dict(request.get("auth", {}))
        policy = deepcopy(dict(request.get("policy_body", {})))
        policy["version"] = str(request["version"])
        updated = self.tools.qso_publish_policy(
            policy=policy,
            actor=str(auth.get("actor", "governance")),
            node_id=str(request.get("node_id", "grpc")),
        )
        return {
            "event_id": f"policy_propose:{policy['version']}",
            "state_hash": _digest(updated),
            "object_uri": str(request["policy_uri"]),
        }

    def ActivatePolicy(self, request: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N802
        # Activation is represented by publishing the requested version.
        auth = dict(request.get("auth", {}))
        current = self.tools.qso_policy_current()
        version = str(request["version"])
        if str(current.get("version", "")) != version:
            current = self.tools.qso_publish_policy(
                policy={**current, "version": version},
                actor=str(auth.get("actor", "governance")),
                node_id=str(request.get("node_id", "grpc")),
            )
        return {
            "event_id": f"policy_activate:{version}:{int(request['activation_index'])}",
            "state_hash": _digest(current),
            "object_uri": str(request["policy_uri"]),
        }


class QSOFederationService:
    """In-process federation handshake service for gRPC transport surfaces."""

    def __init__(self, runtime_version: str = "qso-fabric/0.1.0") -> None:
        self.runtime_version = runtime_version

    def Handshake(self, request: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N802
        remote_runtime = str(request.get("runtime_version", ""))
        if not compatible(self.runtime_version, remote_runtime):
            return {"accepted": False, "reason": "runtime_version_mismatch"}
        if not request.get("policy_set_hash"):
            return {"accepted": False, "reason": "missing_policy_set_hash"}
        if not isinstance(request.get("trust_roots", []), list):
            return {"accepted": False, "reason": "invalid_trust_roots"}
        return {"accepted": True, "reason": "ok"}
