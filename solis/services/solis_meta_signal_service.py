from __future__ import annotations

from math import isfinite
from typing import Any, Dict, List

from solis.config import SolisConfig
from solis.gdml.solis_reward_adapter import SolisRewardAdapter
from solis.identity.zk import generate_collapse_proof, verify_collapse_proof
from solis.integration.gates import GateResult, gate1_deterministic_replay_lock, gate2_invariant_enforcement_lock, gate3_zk_compatibility_lock
from solis.physics.fixed_math import Fixed64
from solis.services.gate_audit import emit_gate_decision
from solis.services.solis_star_service import SolisStarService


class SolisMetaSignalService:
    def __init__(
        self,
        star_service: SolisStarService | None = None,
        config: SolisConfig | None = None,
        reward_adapter: SolisRewardAdapter | None = None,
    ) -> None:
        self.star_service = star_service or SolisStarService()
        self.qso = self.star_service.qso
        self.config = config or SolisConfig()
        self.reward_adapter = reward_adapter or SolisRewardAdapter()

    def emit_signals(self, star_uri_or_id: str, actor: str = "solis.signal") -> Dict[str, float]:
        uri = self.star_service._resolve_star_uri(star_uri_or_id)
        star_id = uri.rsplit(".", 1)[-1]
        timeline = self.star_service.timeline(uri)
        states = self._extract_states(timeline)

        if not states:
            current = self.star_service.get_star(uri).get("state_layer", {})
            states = [current]

        window = max(1, self.config.signal_window)
        samples = states[-window:]
        first = samples[0]
        last = samples[-1]
        steps = max(len(samples) - 1, 1)

        entropy_growth_rate = (float(last.get("entropy_index", 0.0)) - float(first.get("entropy_index", 0.0))) / steps
        fusion_decay = (float(first.get("fusion_rate", 0.0)) - float(last.get("fusion_rate", 0.0))) / steps
        magnetic_values = [float(s.get("magnetic_field", 0.0)) for s in samples]
        magnetic_mean = sum(magnetic_values) / len(magnetic_values)
        magnetic_centralization = abs(float(last.get("magnetic_field", 0.0)) - magnetic_mean)
        collapse_drift_velocity = (
            float(last.get("collapse_probability", 0.0)) - float(first.get("collapse_probability", 0.0))
        ) / steps
        reward = self.reward_adapter.compute_reward(last)

        signals = {
            "entropy_growth_rate": entropy_growth_rate,
            "fusion_decay": fusion_decay,
            "magnetic_centralization": magnetic_centralization,
            "collapse_drift_velocity": collapse_drift_velocity,
            "reward": reward,
        }
        signal_updates = [
            {
                "metric": metric,
                "star_uri": uri,
                "value": signals[metric],
                "window": len(samples),
            }
            for metric in sorted(signals.keys())
        ]

        failed_invariants: list[str] = []
        for metric, value in signals.items():
            if not isfinite(value):
                failed_invariants.append(f"NON_FINITE_SIGNAL_{metric.upper()}")

        computed_collapse = float(last.get("entropy_index", 0.0)) * (
            1.0 - float(last.get("magnetic_field", 0.0))
        ) * float(last.get("fusion_rate", 0.0))
        if computed_collapse < 0.0:
            computed_collapse = 0.0
        if computed_collapse > 1.0:
            computed_collapse = 1.0
        formula_equal = abs(computed_collapse - float(last.get("collapse_probability", 0.0))) <= 0.10

        pre_gate1 = self._run_pre_commit_gates(
            target_uri=uri,
            current_state=dict(last),
            signal_updates=signal_updates,
            failed_invariants=failed_invariants,
            formula_equal=formula_equal,
            entropy=float(last.get("entropy_index", 0.0)),
            magnetic=float(last.get("magnetic_field", 0.0)),
            fusion=float(last.get("fusion_rate", 0.0)),
        )

        emitted_count = 0
        first_event_id = ""
        for metric, value in signals.items():
            signal_uri = f"qso://solis.signal.{metric}.{star_id}"
            if not self.qso.has(signal_uri):
                self.qso.create(signal_uri, {"type": "solis_signal", "metric": metric})
            event = self.qso.patch(
                signal_uri,
                {
                    "star_uri": uri,
                    "metric": metric,
                    "value": value,
                    "window": len(samples),
                },
                actor=actor,
                policy_version=self.config.policy_version,
                node_id=self.config.node_id,
            )
            if not first_event_id:
                first_event_id = str(event.get("event_id", ""))
            emitted_count += 1

        self._run_post_commit_gates(
            target_uri=uri,
            pre_gate1=pre_gate1,
            event_emitted=emitted_count > 0,
            event_id=first_event_id,
        )

        return signals

    def _run_pre_commit_gates(
        self,
        *,
        target_uri: str,
        current_state: Dict[str, Any],
        signal_updates: list[dict[str, Any]],
        failed_invariants: list[str],
        formula_equal: bool,
        entropy: float,
        magnetic: float,
        fusion: float,
    ) -> GateResult:
        if not self.config.runtime_gate_enabled:
            return GateResult(gate="gate1", passed=True, detail="disabled")

        gate1 = gate1_deterministic_replay_lock(
            initial_state=current_state,
            events=[{"delta": update} for update in signal_updates],
            reducer=self._admission_reducer,
            node_ids=list(self.config.runtime_gate_nodes),
        )
        emit_gate_decision(
            qso=self.qso,
            config=self.config,
            scope="signal",
            stage="precommit",
            target_uri=target_uri,
            gate=gate1,
            context={"phase": "gate1", "signal_count": len(signal_updates)},
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
            scope="signal",
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
            scope="signal",
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
        event_emitted: bool,
        event_id: str,
    ) -> None:
        if not self.config.runtime_gate_enabled:
            return
        gate2 = gate2_invariant_enforcement_lock(
            [],
            event_emitted=event_emitted,
            anchor_emitted=True,
            replay_verified=pre_gate1.passed,
        )
        emit_gate_decision(
            qso=self.qso,
            config=self.config,
            scope="signal",
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
            metric = str(delta.get("metric", ""))
            if metric:
                out[f"signal:{metric}"] = delta.get("value", 0.0)
        return out

    @staticmethod
    def _as_fixed(value: float) -> Fixed64:
        return Fixed64.from_str(format(value, ".18g"))

    @staticmethod
    def _extract_states(timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        states: List[Dict[str, Any]] = []
        for event in timeline:
            delta = event.get("delta", {})
            if not isinstance(delta, dict):
                continue
            if "mass" in delta and "entropy_index" in delta:
                states.append(delta)
        return states
