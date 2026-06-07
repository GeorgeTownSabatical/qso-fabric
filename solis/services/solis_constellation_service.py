from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, cast

from solis.config import SolisConfig
from solis.gdml.solis_optimizer import SolisOptimizer
from solis.identity.zk import generate_collapse_proof, verify_collapse_proof
from solis.integration.gates import GateResult, gate1_deterministic_replay_lock, gate2_invariant_enforcement_lock, gate3_zk_compatibility_lock
from solis.physics.fixed_math import Fixed64
from solis.schemas import SCHEMA_VERSION
from solis.services.gate_audit import emit_gate_decision
from solis.services.solis_star_service import SolisStarService

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"


class SolisConstellationService:
    def __init__(
        self,
        star_service: SolisStarService | None = None,
        config: SolisConfig | None = None,
        optimizer: SolisOptimizer | None = None,
    ) -> None:
        self.star_service = star_service or SolisStarService()
        self.config = config or SolisConfig()
        self.qso = self.star_service.qso
        self.optimizer = optimizer or SolisOptimizer(getattr(self.qso, "tools", None))
        self.constellation_schema = self._load_schema("constellation.schema.json")

    @staticmethod
    def constellation_uri(domain: str) -> str:
        return f"qso://solis.constellation.{domain}"

    def create_constellation(
        self,
        *,
        domain: str,
        star_uris: Iterable[str],
        actor: str = "solis.constellation",
    ) -> Dict[str, Any]:
        uri = self.constellation_uri(domain)
        star_list = [self._normalize_star_uri(value) for value in star_uris]
        if not star_list:
            raise ValueError("constellation requires at least one star")

        if not self.qso.has(uri):
            self.qso.create(uri, self.constellation_schema)
        current_state = self.qso.read(uri).get("state_layer", {})

        payload = {
            "schema_version": SCHEMA_VERSION,
            "constellation_id": domain,
            "domain": domain,
            "star_uris": star_list,
            "contagion_index": 0.0,
            "cascade_threshold": self.config.cascade_threshold,
            "collapse_count": 0,
            "cascade_detected": False,
        }
        pre_gate1 = self._run_pre_commit_gates(
            target_uri=uri,
            current_state=current_state,
            projected_patch=payload,
            input_delta={"create": True, "star_count": len(star_list)},
            failed_invariants=[],
            formula_equal=True,
            entropy=0.0,
            magnetic=1.0,
            fusion=1.0,
        )

        event = self.qso.patch(
            uri,
            payload,
            actor=actor,
            policy_version=self.config.policy_version,
            node_id=self.config.node_id,
        )
        self._run_post_commit_gates(target_uri=uri, pre_gate1=pre_gate1, event_id=str(event.get("event_id", "")))

        self._entangle_constellation(star_list)
        return self.qso.read(uri)

    def recompute_constellation(self, domain_or_uri: str, actor: str = "solis.constellation") -> Dict[str, Any]:
        uri = self._resolve_constellation_uri(domain_or_uri)
        constellation = self.qso.read(uri)
        state = constellation.get("state_layer", {})
        star_uris = [self._normalize_star_uri(value) for value in state.get("star_uris", [])]
        if not star_uris:
            raise ValueError(f"constellation has no stars: {uri}")

        star_states = [self.star_service.get_star(star_uri).get("state_layer", {}) for star_uri in star_uris]

        collapse_values = [float(s.get("collapse_probability", 0.0)) for s in star_states]
        entropy_values = [float(s.get("entropy_index", 0.0)) for s in star_states]
        magnetic_values = [float(s.get("magnetic_field", 0.0)) for s in star_states]

        collapse_mean = sum(collapse_values) / len(collapse_values)
        entropy_mean = sum(entropy_values) / len(entropy_values)
        magnetic_mean = sum(magnetic_values) / len(magnetic_values)

        entropy_dispersion = sum(abs(value - entropy_mean) for value in entropy_values) / len(entropy_values)
        contagion_index = _clamp((collapse_mean * 0.65) + (entropy_dispersion * 0.20) + ((1.0 - magnetic_mean) * 0.15))

        collapse_count = sum(1 for value in collapse_values if value >= self.config.collapse_warning_threshold)
        cascade_threshold = float(state.get("cascade_threshold", self.config.cascade_threshold))
        cascade_detected = bool(contagion_index >= cascade_threshold or collapse_count > 0)

        patch = {
            "contagion_index": contagion_index,
            "collapse_count": collapse_count,
            "cascade_detected": cascade_detected,
            "collapse_mean": collapse_mean,
            "entropy_mean": entropy_mean,
            "magnetic_mean": magnetic_mean,
        }
        failed_invariants: list[str] = []
        if not (0.0 <= contagion_index <= 1.0):
            failed_invariants.append("CONTAGION_BOUND_EXCEEDED")
        if collapse_count < 0:
            failed_invariants.append("NEGATIVE_COLLAPSE_COUNT")
        if not (0.0 <= cascade_threshold <= 1.0):
            failed_invariants.append("INVALID_CASCADE_THRESHOLD")

        expected_contagion = _clamp((collapse_mean * 0.65) + (entropy_dispersion * 0.20) + ((1.0 - magnetic_mean) * 0.15))
        formula_equal = abs(expected_contagion - contagion_index) <= 1e-12
        pre_gate1 = self._run_pre_commit_gates(
            target_uri=uri,
            current_state=state,
            projected_patch=patch,
            input_delta={"recompute": True, "star_count": len(star_uris)},
            failed_invariants=failed_invariants,
            formula_equal=formula_equal,
            entropy=entropy_mean,
            magnetic=magnetic_mean,
            fusion=max(0.0, 1.0 - collapse_mean),
        )

        event = self.qso.patch(
            uri,
            patch,
            actor=actor,
            policy_version=self.config.policy_version,
            node_id=self.config.node_id,
        )
        self._run_post_commit_gates(target_uri=uri, pre_gate1=pre_gate1, event_id=str(event.get("event_id", "")))

        if cascade_detected:
            self._propagate_cascade(star_uris, magnitude=contagion_index, actor="solis.cascade")

        optimizer_output = self.optimizer.propose(
            constellation_uri=uri,
            metrics={
                "contagion_index": contagion_index,
                "collapse_mean": collapse_mean,
                "entropy_mean": entropy_mean,
            },
            actor="solis.optimizer",
        )

        return {
            "uri": uri,
            "event_id": event["event_id"],
            "contagion_index": contagion_index,
            "collapse_count": collapse_count,
            "cascade_detected": cascade_detected,
            "optimizer": optimizer_output,
        }

    def propagate_from_star(
        self,
        *,
        domain_or_uri: str,
        source_star_uri: str,
        event_type: str,
        magnitude: float = 1.0,
        actor: str = "solis.propagation",
    ) -> Dict[str, Any]:
        uri = self._resolve_constellation_uri(domain_or_uri)
        constellation = self.qso.read(uri)
        star_uris = [self._normalize_star_uri(value) for value in constellation.get("state_layer", {}).get("star_uris", [])]

        source_uri = self._normalize_star_uri(source_star_uri)
        impacted: List[str] = []
        for target_uri in star_uris:
            if target_uri == source_uri:
                continue
            self.star_service.apply_relationship(
                star_uri_or_id=target_uri,
                event_type=event_type,
                magnitude=magnitude,
                reverse=False,
                actor=actor,
            )
            impacted.append(target_uri)

        summary = {
            "source_star_uri": source_uri,
            "event_type": event_type,
            "magnitude": magnitude,
            "impacted_stars": impacted,
        }
        failed_invariants: list[str] = []
        if magnitude < 0.0:
            failed_invariants.append("NEGATIVE_PROPAGATION_MAGNITUDE")
        pre_gate1 = self._run_pre_commit_gates(
            target_uri=uri,
            current_state=constellation.get("state_layer", {}),
            projected_patch={"last_propagation": summary},
            input_delta={"propagate": True, "event_type": event_type},
            failed_invariants=failed_invariants,
            formula_equal=True,
            entropy=0.0,
            magnetic=1.0,
            fusion=1.0,
        )
        event = self.qso.patch(
            uri,
            {"last_propagation": summary},
            actor=actor,
            policy_version=self.config.policy_version,
            node_id=self.config.node_id,
        )
        self._run_post_commit_gates(target_uri=uri, pre_gate1=pre_gate1, event_id=str(event.get("event_id", "")))
        return summary

    def timeline(self, domain_or_uri: str, strict: bool = True) -> list[Dict[str, Any]]:
        uri = self._resolve_constellation_uri(domain_or_uri)
        return self.qso.timeline(uri, strict=strict)

    def _entangle_constellation(self, star_uris: list[str]) -> None:
        for source in star_uris:
            for target in star_uris:
                if source == target:
                    continue
                try:
                    self.qso.entangle(source, target, "solis_constellation_propagation")
                except ValueError:
                    # Existing links or cycle constraints are non-fatal for deterministic setup.
                    continue

    def _propagate_cascade(self, star_uris: list[str], magnitude: float, actor: str) -> None:
        for star_uri in star_uris:
            self.star_service.apply_relationship(
                star_uri_or_id=star_uri,
                event_type="governance_vote_spike",
                magnitude=max(magnitude, 0.05),
                actor=actor,
            )

    def _run_pre_commit_gates(
        self,
        *,
        target_uri: str,
        current_state: Dict[str, Any],
        projected_patch: Dict[str, Any],
        input_delta: Dict[str, Any],
        failed_invariants: list[str],
        formula_equal: bool,
        entropy: float,
        magnetic: float,
        fusion: float,
    ) -> GateResult:
        if not self.config.runtime_gate_enabled:
            return GateResult(gate="gate1", passed=True, detail="disabled")

        gate1 = gate1_deterministic_replay_lock(
            initial_state=dict(current_state),
            events=[{"delta": dict(projected_patch), "input_delta": dict(input_delta)}],
            reducer=self._admission_reducer,
            node_ids=list(self.config.runtime_gate_nodes),
        )
        emit_gate_decision(
            qso=self.qso,
            config=self.config,
            scope="constellation",
            stage="precommit",
            target_uri=target_uri,
            gate=gate1,
            context={"phase": "gate1"},
        )
        if not gate1.passed:
            raise ValueError(f"runtime_gate: gate1 rejected ({gate1.detail})")

        gate2 = gate2_invariant_enforcement_lock(
            failed_invariants,
            event_emitted=True,
            anchor_emitted=True,
            replay_verified=gate1.passed,
        )
        emit_gate_decision(
            qso=self.qso,
            config=self.config,
            scope="constellation",
            stage="precommit",
            target_uri=target_uri,
            gate=gate2,
            context={"phase": "gate2", "failed_invariants": failed_invariants},
        )
        if not gate2.passed:
            raise ValueError(f"runtime_gate: gate2 rejected ({gate2.detail})")

        proof_verified = True
        if self.config.require_zk_proof:
            proof = generate_collapse_proof(
                entropy=self._as_fixed(entropy),
                magnetic=self._as_fixed(magnetic),
                fusion=self._as_fixed(fusion),
                threshold=Fixed64.one(),
            )
            proof_verified = verify_collapse_proof(proof)
        gate3 = gate3_zk_compatibility_lock(
            formula_equal=formula_equal,
            proof_verified=proof_verified if self.config.require_zk_proof else True,
            fixed_point_only=True,
        )
        emit_gate_decision(
            qso=self.qso,
            config=self.config,
            scope="constellation",
            stage="precommit",
            target_uri=target_uri,
            gate=gate3,
            context={"phase": "gate3", "require_zk_proof": self.config.require_zk_proof},
        )
        if not gate3.passed:
            raise ValueError(f"runtime_gate: gate3 rejected ({gate3.detail})")

        return gate1

    def _run_post_commit_gates(self, *, target_uri: str, pre_gate1: GateResult, event_id: str) -> None:
        if not self.config.runtime_gate_enabled:
            return
        gate2 = gate2_invariant_enforcement_lock(
            [],
            event_emitted=bool(event_id),
            anchor_emitted=True,
            replay_verified=pre_gate1.passed,
        )
        emit_gate_decision(
            qso=self.qso,
            config=self.config,
            scope="constellation",
            stage="postcommit",
            target_uri=target_uri,
            gate=gate2,
            context={"phase": "gate2", "event_id": event_id},
        )
        if not gate2.passed:
            raise ValueError(f"runtime_gate: post-commit gate2 rejected ({gate2.detail})")

    @staticmethod
    def _admission_reducer(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        out = dict(state)
        delta = event.get("delta", {})
        if isinstance(delta, dict):
            for key, value in delta.items():
                out[str(key)] = value
        return out

    @staticmethod
    def _as_fixed(value: float) -> Fixed64:
        return Fixed64.from_str(format(value, ".18g"))

    @staticmethod
    def _load_schema(filename: str) -> Dict[str, Any]:
        path = SCHEMA_DIR / filename
        with path.open("r", encoding="utf-8") as handle:
            return cast(Dict[str, Any], json.load(handle))

    def _resolve_constellation_uri(self, domain_or_uri: str) -> str:
        value = str(domain_or_uri).strip()
        if value.startswith("qso://solis.constellation."):
            return value
        return self.constellation_uri(value)

    @staticmethod
    def _normalize_star_uri(star_uri_or_id: str) -> str:
        value = str(star_uri_or_id).strip()
        if value.startswith("qso://solis.star."):
            return value
        return f"qso://solis.star.{value}"


def _clamp(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value
