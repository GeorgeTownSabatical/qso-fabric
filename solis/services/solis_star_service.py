from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, Mapping, Protocol, cast

from api.mcp_tools.qso_tools import QSOMCPTools
from solis.agent.runtime.policy_guard import PolicyGuard, PolicyGuardDecision
from solis.config import SPHERECHAIN_STAR_URI, SolisConfig
from solis.entanglement.stellar_relationships import StellarRelationshipEffect, relationship_delta
from solis.gdml.solis_policy_sync import SolisPolicySync
from solis.gdml.solis_reward_adapter import SolisRewardAdapter
from solis.identity.zk import generate_collapse_proof, verify_collapse_proof
from solis.integration.gates import GateResult, gate1_deterministic_replay_lock, gate2_invariant_enforcement_lock, gate3_zk_compatibility_lock
from solis.merkle.merkle_anchor import StellarMerkleAnchor
from solis.physics.fixed_math import Fixed64
from solis.projectors.stellar_projector_v1 import StellarState, project_stellar_v1
from solis.schemas import SCHEMA_VERSION
from solis.services.gate_audit import emit_gate_decision

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"


class QSOInterface(Protocol):
    def create(self, uri: str, schema: Dict[str, Any]) -> Dict[str, Any]: ...

    def read(self, uri: str) -> Dict[str, Any]: ...

    def patch(
        self,
        uri: str,
        delta: Dict[str, Any],
        *,
        actor: str,
        policy_version: str,
        node_id: str,
    ) -> Dict[str, Any]: ...

    def timeline(self, uri: str, strict: bool = True) -> list[Dict[str, Any]]: ...

    def entangle(self, uri_a: str, uri_b: str, relationship: str) -> Dict[str, Any]: ...

    def has(self, uri: str) -> bool: ...

    def sign(self, payload: str) -> str: ...


class SolisQSOBridge:
    """Adapter that exposes a stable qso.create/read/patch/timeline surface."""

    def __init__(self, tools: QSOMCPTools | None = None) -> None:
        self.tools = tools or QSOMCPTools()

    def create(self, uri: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        return cast(Dict[str, Any], self.tools.qso_create(uri, schema))

    def read(self, uri: str) -> Dict[str, Any]:
        return cast(Dict[str, Any], self.tools.qso_read(uri))

    def patch(
        self,
        uri: str,
        delta: Dict[str, Any],
        *,
        actor: str,
        policy_version: str,
        node_id: str,
    ) -> Dict[str, Any]:
        return cast(
            Dict[str, Any],
            self.tools.qso_patch(
                uri=uri,
                delta=delta,
                actor=actor,
                policy_version=policy_version,
                node_id=node_id,
            ),
        )

    def timeline(self, uri: str, strict: bool = True) -> list[Dict[str, Any]]:
        return cast(list[Dict[str, Any]], self.tools.qso_timeline(uri, strict=strict))

    def entangle(self, uri_a: str, uri_b: str, relationship: str) -> Dict[str, Any]:
        return cast(Dict[str, Any], self.tools.qso_entangle(uri_a, uri_b, relationship, bidirectional=False))

    def has(self, uri: str) -> bool:
        return cast(bool, self.tools.runtime.registry.has(uri))

    def sign(self, payload: str) -> str:
        return cast(str, self.tools.runtime.crypto.sign(payload))


class SolisStarService:
    def __init__(
        self,
        qso: QSOInterface | None = None,
        config: SolisConfig | None = None,
        merkle_anchor: StellarMerkleAnchor | None = None,
        policy_sync: SolisPolicySync | None = None,
        reward_adapter: SolisRewardAdapter | None = None,
        policy_gate: PolicyGuard | None = None,
    ) -> None:
        self.qso = qso or SolisQSOBridge()
        self.config = config or SolisConfig()
        self.star_schema = self._load_schema("star.schema.json")
        self.stellar_event_schema = self._load_schema("stellar_event.schema.json")
        self.merkle_anchor = merkle_anchor or StellarMerkleAnchor(epoch_size=self.config.anchor_interval)
        self.policy_sync = policy_sync or SolisPolicySync()
        self.reward_adapter = reward_adapter or SolisRewardAdapter()
        self.policy_gate = policy_gate or PolicyGuard()

    @staticmethod
    def star_uri(star_id: str) -> str:
        return f"qso://solis.star.{star_id}"

    def create_star(
        self,
        *,
        star_id: str,
        chain_id: str,
        initial_state: Mapping[str, float] | None = None,
        actor: str = "solis.bootstrap",
    ) -> Dict[str, Any]:
        uri = self.star_uri(star_id)
        if not self.qso.has(uri):
            self.qso.create(uri, self.star_schema)

        base_state: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "star_id": star_id,
            "chain_id": chain_id,
            "mass": 1.0,
            "luminosity": 1.0,
            "core_temp": 1.0,
            "magnetic_field": 1.0,
            "entropy_index": 0.05,
            "fusion_rate": 1.0,
            "collapse_probability": 0.0,
        }
        if initial_state:
            for key, value in initial_state.items():
                base_state[str(key)] = self._as_projection_float(value)

        self._validate_schema(base_state, self.star_schema, name="star")
        event = self.qso.patch(
            uri,
            base_state,
            actor=actor,
            policy_version=self.config.policy_version,
            node_id=self.config.node_id,
        )
        self._emit_stellar_event(
            object_uri=uri,
            event=event,
            input_delta={"create": True},
            projected_state=base_state,
            relationship=None,
        )
        return self.qso.read(uri)

    def get_star(self, star_uri_or_id: str) -> Dict[str, Any]:
        uri = self._resolve_star_uri(star_uri_or_id)
        return self.qso.read(uri)

    def patch_star(
        self,
        *,
        star_uri_or_id: str,
        delta: Mapping[str, float] | None = None,
        actor: str = "solis.engine",
        relationship_event: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        uri = self._resolve_star_uri(star_uri_or_id)
        obj = self.qso.read(uri)
        current = StellarState.from_mapping(obj.get("state_layer", {}))

        projection_delta = self._projection_delta(delta or {})
        relationship = self._relationship_effect(relationship_event)
        if relationship is not None:
            projection_delta = self._merge_numeric_delta(projection_delta, relationship.delta)

        core_temp_spike = self._as_projection_float(projection_delta.pop("core_temp_spike", 0.0))
        projected = project_stellar_v1(current, projection_delta)
        if core_temp_spike:
            projected = replace(projected, core_temp=max(projected.core_temp + core_temp_spike, 0.0))

        projected_payload = projected.as_dict()
        projected_payload["schema_version"] = str(obj.get("state_layer", {}).get("schema_version", SCHEMA_VERSION))
        decision = self.policy_gate.evaluate_transition(current.as_dict(), projected_payload)
        if not decision.allowed:
            reasons = ",".join(decision.reason_codes)
            raise ValueError(f"policy_guard: transition rejected ({reasons})")

        pre_gate1 = self._run_pre_commit_gates(
            target_uri=uri,
            current_state=current.as_dict(),
            projected_state=projected_payload,
            input_delta=dict(delta or {}),
            decision=decision,
        )
        self._validate_schema(projected_payload, self.star_schema, name="star")

        event = self.qso.patch(
            uri,
            projected_payload,
            actor=actor,
            policy_version=self.config.policy_version,
            node_id=self.config.node_id,
        )

        stellar_event = self._emit_stellar_event(
            object_uri=uri,
            event=event,
            input_delta=dict(delta or {}),
            projected_state=projected_payload,
            relationship=relationship,
        )
        self._run_post_commit_gates(target_uri=uri, pre_gate1=pre_gate1, stellar_event=stellar_event)
        self._emit_reward_signal(uri=uri, state=projected_payload)

        return {
            "uri": uri,
            "stellar_event": stellar_event,
            "state": projected_payload,
        }

    def apply_policy_event(
        self,
        *,
        star_uri_or_id: str,
        policy: Mapping[str, Any],
        actor: str = "solis.policy",
    ) -> Dict[str, Any]:
        uri = self._resolve_star_uri(star_uri_or_id)
        current_obj = self.qso.read(uri)
        current = StellarState.from_mapping(current_obj.get("state_layer", {}))
        next_state = self.policy_sync.apply_policy(current, policy)
        projected_payload = next_state.as_dict()
        projected_payload["schema_version"] = str(
            current_obj.get("state_layer", {}).get("schema_version", SCHEMA_VERSION)
        )
        decision = self.policy_gate.evaluate_transition(current.as_dict(), projected_payload)
        if not decision.allowed:
            reasons = ",".join(decision.reason_codes)
            raise ValueError(f"policy_guard: transition rejected ({reasons})")

        pre_gate1 = self._run_pre_commit_gates(
            target_uri=uri,
            current_state=current.as_dict(),
            projected_state=projected_payload,
            input_delta={"policy": dict(policy)},
            decision=decision,
        )

        event = self.qso.patch(
            uri,
            projected_payload,
            actor=actor,
            policy_version=self.config.policy_version,
            node_id=self.config.node_id,
        )
        stellar_event = self._emit_stellar_event(
            object_uri=uri,
            event=event,
            input_delta={"policy": dict(policy)},
            projected_state=projected_payload,
            relationship=None,
        )
        self._run_post_commit_gates(target_uri=uri, pre_gate1=pre_gate1, stellar_event=stellar_event)
        self._emit_reward_signal(uri=uri, state=projected_payload)
        return {"uri": uri, "stellar_event": stellar_event, "state": projected_payload}

    def apply_relationship(
        self,
        *,
        star_uri_or_id: str,
        event_type: str,
        magnitude: float = 1.0,
        reverse: bool = False,
        actor: str = "solis.entanglement",
    ) -> Dict[str, Any]:
        return self.patch_star(
            star_uri_or_id=star_uri_or_id,
            delta={},
            actor=actor,
            relationship_event={
                "event_type": event_type,
                "magnitude": magnitude,
                "reverse": reverse,
            },
        )

    def timeline(self, star_uri_or_id: str, strict: bool = True) -> list[Dict[str, Any]]:
        uri = self._resolve_star_uri(star_uri_or_id)
        return self.qso.timeline(uri, strict=strict)

    def _emit_stellar_event(
        self,
        *,
        object_uri: str,
        event: Mapping[str, Any],
        input_delta: Mapping[str, Any],
        projected_state: Mapping[str, Any],
        relationship: StellarRelationshipEffect | None,
    ) -> Dict[str, Any]:
        event_id = str(event["event_id"])
        star_id = object_uri.rsplit(".", 1)[-1]
        event_uri = f"qso://solis.stellar_event.{star_id}.{event_id}"

        if not self.qso.has(event_uri):
            self.qso.create(event_uri, self.stellar_event_schema)

        payload: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "event_id": event_id,
            "timestamp": str(event["timestamp"]),
            "actor": str(event["actor"]),
            "object_uri": object_uri,
            "delta": dict(input_delta),
            "stellar_projection": dict(projected_state),
            "signature": str(event["signature"]),
            "policy_version": str(event["policy_version"]),
        }
        if relationship is not None:
            payload["relationship"] = {
                "event_type": relationship.event_type,
                "magnitude": relationship.magnitude,
                "delta": dict(relationship.delta),
                "inverse_delta": dict(relationship.inverse_delta),
            }

        self._validate_schema(payload, self.stellar_event_schema, name="stellar_event")
        self.qso.patch(
            event_uri,
            payload,
            actor="solis.eventlog",
            policy_version=self.config.policy_version,
            node_id=self.config.node_id,
        )

        hash_material: Dict[str, Any] = {
            "schema_version": payload["schema_version"],
            "object_uri": payload["object_uri"],
            "actor": payload["actor"],
            "delta": payload["delta"],
            "stellar_projection": payload["stellar_projection"],
            "policy_version": payload["policy_version"],
        }
        if relationship is not None:
            hash_material["relationship"] = payload["relationship"]
        serialized = json.dumps(hash_material, sort_keys=True, separators=(",", ":"))
        self.merkle_anchor.append_event(serialized)

        anchor_payload: Dict[str, Any] | None = None
        if self.merkle_anchor.should_anchor():
            anchor_payload = self._emit_anchor_event(actor="solis.anchor")
            payload["merkle_root"] = anchor_payload["root"]
            payload["anchor_epoch"] = anchor_payload["epoch"]

        return payload

    def _emit_anchor_event(self, actor: str) -> Dict[str, Any]:
        epoch = self.merkle_anchor.epoch()
        root = self.merkle_anchor.root()
        signature = self.qso.sign(root)
        uri = f"qso://solis.anchor.{epoch}"

        if not self.qso.has(uri):
            self.qso.create(uri, {"type": "solis_merkle_anchor"})

        payload = {
            "epoch": epoch,
            "root": root,
            "signature": signature,
            "event_count": len(self.merkle_anchor.event_hashes),
        }
        self.qso.patch(
            uri,
            payload,
            actor=actor,
            policy_version=self.config.policy_version,
            node_id=self.config.node_id,
        )
        return payload

    def _run_pre_commit_gates(
        self,
        *,
        target_uri: str,
        current_state: Mapping[str, Any],
        projected_state: Mapping[str, Any],
        input_delta: Mapping[str, Any],
        decision: PolicyGuardDecision,
    ) -> GateResult:
        if not self.config.runtime_gate_enabled:
            return GateResult(gate="gate1", passed=True, detail="disabled")

        gate1 = gate1_deterministic_replay_lock(
            initial_state=dict(current_state),
            events=[
                {
                    "delta": dict(projected_state),
                    "input_delta": dict(input_delta),
                    "policy_version": self.config.policy_version,
                }
            ],
            reducer=self._admission_reducer,
            node_ids=list(self.config.runtime_gate_nodes),
        )
        emit_gate_decision(
            qso=self.qso,
            config=self.config,
            scope="star",
            stage="precommit",
            target_uri=target_uri,
            gate=gate1,
            context={"phase": "gate1", "input_delta": dict(input_delta)},
        )
        if not gate1.passed:
            raise ValueError(f"runtime_gate: gate1 rejected ({gate1.detail})")

        failed_invariants = [code for code in decision.reason_codes if code != "OK"]
        gate2 = gate2_invariant_enforcement_lock(
            failed_invariants,
            event_emitted=True,
            anchor_emitted=True,
            replay_verified=gate1.passed,
        )
        emit_gate_decision(
            qso=self.qso,
            config=self.config,
            scope="star",
            stage="precommit",
            target_uri=target_uri,
            gate=gate2,
            context={"phase": "gate2", "failed_invariants": failed_invariants},
        )
        if not gate2.passed:
            raise ValueError(f"runtime_gate: gate2 rejected ({gate2.detail})")

        entropy = self._as_fixed(projected_state.get("entropy_index", 0.0))
        magnetic = self._as_fixed(projected_state.get("magnetic_field", 1.0))
        fusion = self._as_fixed(projected_state.get("fusion_rate", 0.0))
        proof = generate_collapse_proof(
            entropy=entropy,
            magnetic=magnetic,
            fusion=fusion,
            threshold=Fixed64.one(),
        )
        proof_verified = verify_collapse_proof(proof)
        declared_collapse = self._as_fixed(projected_state.get("collapse_probability", 0.0))
        tolerance = self.policy_gate.collapse_consistency_tolerance
        formula_equal = abs(declared_collapse - decision.computed_collapse_probability) <= tolerance
        gate3 = gate3_zk_compatibility_lock(
            formula_equal=formula_equal,
            proof_verified=(proof_verified if self.config.require_zk_proof else True),
            fixed_point_only=True,
        )
        emit_gate_decision(
            qso=self.qso,
            config=self.config,
            scope="star",
            stage="precommit",
            target_uri=target_uri,
            gate=gate3,
            context={"phase": "gate3", "require_zk_proof": self.config.require_zk_proof},
        )
        if not gate3.passed:
            raise ValueError(f"runtime_gate: gate3 rejected ({gate3.detail})")

        return gate1

    def _run_post_commit_gates(
        self,
        *,
        target_uri: str,
        pre_gate1: GateResult,
        stellar_event: Mapping[str, Any],
    ) -> None:
        if not self.config.runtime_gate_enabled:
            return
        anchor_required = (
            bool(self.merkle_anchor.event_hashes)
            and (len(self.merkle_anchor.event_hashes) % self.merkle_anchor.epoch_size == 0)
        )
        gate2 = gate2_invariant_enforcement_lock(
            [],
            event_emitted=bool(stellar_event.get("event_id")),
            anchor_emitted=(not anchor_required) or ("merkle_root" in stellar_event and "anchor_epoch" in stellar_event),
            replay_verified=pre_gate1.passed,
        )
        emit_gate_decision(
            qso=self.qso,
            config=self.config,
            scope="star",
            stage="postcommit",
            target_uri=target_uri,
            gate=gate2,
            context={"phase": "gate2", "event_id": str(stellar_event.get("event_id", ""))},
        )
        if not gate2.passed:
            raise ValueError(f"runtime_gate: post-commit gate2 rejected ({gate2.detail})")

    def _resolve_star_uri(self, star_uri_or_id: str) -> str:
        value = str(star_uri_or_id).strip()
        if value.startswith("qso://solis.star."):
            return value
        return self.star_uri(value)

    def _emit_reward_signal(self, *, uri: str, state: Mapping[str, Any]) -> None:
        star_id = uri.rsplit(".", 1)[-1]
        signal_uri = f"qso://solis.signal.reward.{star_id}"
        if not self.qso.has(signal_uri):
            self.qso.create(signal_uri, {"type": "solis_reward_signal"})

        reward = self.reward_adapter.compute_reward(state)
        payload = {
            "star_uri": uri,
            "metric": "reward",
            "value": reward,
            "collapse_probability": float(state.get("collapse_probability", 0.0)),
            "fusion_rate": float(state.get("fusion_rate", 0.0)),
            "entropy_index": float(state.get("entropy_index", 0.0)),
        }
        self.qso.patch(
            signal_uri,
            payload,
            actor="solis.reward",
            policy_version=self.config.policy_version,
            node_id=self.config.node_id,
        )

    @staticmethod
    def _projection_delta(delta: Mapping[str, float]) -> Dict[str, float]:
        allowed = {
            "mass",
            "luminosity",
            "entropy_index",
            "magnetic_field",
            "core_temp_spike",
        }
        out: Dict[str, float] = {}
        for key, value in delta.items():
            key_name = str(key)
            if key_name not in allowed:
                continue
            out[key_name] = SolisStarService._as_projection_float(value)
        return out

    @staticmethod
    def _admission_reducer(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        out = dict(state)
        delta = event.get("delta", {})
        if isinstance(delta, dict):
            for key, value in delta.items():
                out[str(key)] = value
        return out

    @staticmethod
    def _as_fixed(value: Any) -> Fixed64:
        if isinstance(value, Fixed64):
            return value
        if isinstance(value, int):
            return Fixed64.from_int(value)
        if isinstance(value, float):
            return Fixed64.from_str(format(value, ".18g"))
        if isinstance(value, str):
            return Fixed64.from_str(value)
        return Fixed64.zero()

    @staticmethod
    def _as_projection_float(value: Any) -> float:
        return float(SolisStarService._as_fixed(value).to_str(18))

    @staticmethod
    def _merge_numeric_delta(a: Mapping[str, float], b: Mapping[str, float]) -> Dict[str, float]:
        merged: Dict[str, float] = dict(a)
        for key, value in b.items():
            lhs = SolisStarService._as_fixed(merged.get(key, 0.0))
            rhs = SolisStarService._as_fixed(value)
            merged[key] = float((lhs + rhs).to_str(18))
        return merged

    @staticmethod
    def _relationship_effect(event: Mapping[str, Any] | None) -> StellarRelationshipEffect | None:
        if not event:
            return None
        event_type = str(event.get("event_type", "")).strip()
        if not event_type:
            return None
        magnitude = SolisStarService._as_projection_float(event.get("magnitude", 1.0))
        reverse = bool(event.get("reverse", False))
        return relationship_delta(event_type, magnitude=magnitude, reverse=reverse)

    @staticmethod
    def _load_schema(filename: str) -> Dict[str, Any]:
        path = SCHEMA_DIR / filename
        with path.open("r", encoding="utf-8") as handle:
            return cast(Dict[str, Any], json.load(handle))

    def _validate_schema(self, payload: Mapping[str, Any], schema: Mapping[str, Any], *, name: str) -> None:
        if schema.get("type") != "object":
            raise ValueError(f"{name}: only object schemas are supported")

        required = schema.get("required", [])
        for field in required:
            if field not in payload:
                raise ValueError(f"{name}: missing required field '{field}'")

        properties = schema.get("properties", {})
        additional_ok = bool(schema.get("additionalProperties", True))
        for field, value in payload.items():
            if field not in properties:
                if additional_ok:
                    continue
                raise ValueError(f"{name}: unknown field '{field}'")
            self._validate_field(name=name, field=field, value=value, rules=properties[field])

    @staticmethod
    def _validate_field(*, name: str, field: str, value: Any, rules: Mapping[str, Any]) -> None:
        expected = rules.get("type")
        if expected == "string" and not isinstance(value, str):
            raise ValueError(f"{name}: field '{field}' must be string")
        if expected == "number" and not isinstance(value, (int, float)):
            raise ValueError(f"{name}: field '{field}' must be number")
        if expected == "integer" and not isinstance(value, int):
            raise ValueError(f"{name}: field '{field}' must be integer")
        if expected == "object" and not isinstance(value, dict):
            raise ValueError(f"{name}: field '{field}' must be object")
        if expected == "boolean" and not isinstance(value, bool):
            raise ValueError(f"{name}: field '{field}' must be boolean")
        if expected == "array" and not isinstance(value, list):
            raise ValueError(f"{name}: field '{field}' must be array")

        if isinstance(value, (int, float)) and "minimum" in rules and value < float(rules["minimum"]):
            raise ValueError(f"{name}: field '{field}' below minimum")
        if isinstance(value, (int, float)) and "maximum" in rules and value > float(rules["maximum"]):
            raise ValueError(f"{name}: field '{field}' above maximum")


def bootstrap_spherechain_star(service: SolisStarService | None = None) -> Dict[str, Any]:
    runtime = service or SolisStarService()
    return runtime.create_star(star_id="spherechain", chain_id="spherechain")


if __name__ == "__main__":
    bootstrap_spherechain_star()
    print(f"Solis Star Service initialized: {SPHERECHAIN_STAR_URI}")
