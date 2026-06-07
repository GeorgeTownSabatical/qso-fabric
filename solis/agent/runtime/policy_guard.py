from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from solis.physics.collapse_engine import collapse_probability_v1
from solis.physics.fixed_math import Fixed64
from solis.physics.invariants import GlobalState, InvariantLimits, evaluate_global_invariants


@dataclass(frozen=True)
class PolicyGuardDecision:
    allowed: bool
    reason_codes: tuple[str, ...]
    computed_collapse_probability: Fixed64


class PolicyGuard:
    """Deterministic pre-execution guard for Solis transitions."""

    def __init__(
        self,
        *,
        limits: InvariantLimits | None = None,
        collapse_consistency_tolerance: Fixed64 | None = None,
        allowed_transition_fields: frozenset[str] | None = None,
    ) -> None:
        self.limits = limits or InvariantLimits(
            max_entropy_growth=Fixed64.from_str("5.0"),
            max_collapse_probability=Fixed64.one(),
            max_leverage_ratio=Fixed64.from_str("100.0"),
            max_contagion_index=Fixed64.one(),
            capital_tolerance=Fixed64.from_int(1_000_000),
        )
        self.collapse_consistency_tolerance = collapse_consistency_tolerance or Fixed64.from_str("0.05")
        self.allowed_transition_fields = allowed_transition_fields or frozenset(
            {
                "schema_version",
                "star_id",
                "chain_id",
                "mass",
                "luminosity",
                "core_temp",
                "magnetic_field",
                "entropy_index",
                "fusion_rate",
                "collapse_probability",
                "capital_total",
                "leverage_ratio",
                "contagion_index",
                "collapse_count",
                "collapse_mean",
                "entropy_mean",
                "magnetic_mean",
                "cascade_threshold",
                "cascade_detected",
                "last_propagation",
            }
        )

    def evaluate_transition(
        self,
        current: Mapping[str, Any],
        proposed: Mapping[str, Any],
    ) -> PolicyGuardDecision:
        disallowed_fields = sorted(
            field for field in proposed.keys() if str(field) not in self.allowed_transition_fields
        )
        if disallowed_fields:
            reason_codes = tuple(f"FIELD_NOT_ALLOWED:{field}" for field in disallowed_fields)
            return PolicyGuardDecision(
                allowed=False,
                reason_codes=reason_codes,
                computed_collapse_probability=Fixed64.zero(),
            )

        next_mass = self._read_fixed(proposed, current, "mass", default="0")
        if next_mass <= Fixed64.zero():
            return PolicyGuardDecision(
                allowed=False,
                reason_codes=("MASS_NON_POSITIVE",),
                computed_collapse_probability=Fixed64.zero(),
            )

        next_entropy = self._read_fixed(proposed, current, "entropy_index", default="0")
        if next_entropy < Fixed64.zero():
            return PolicyGuardDecision(
                allowed=False,
                reason_codes=("NEGATIVE_ENTROPY",),
                computed_collapse_probability=Fixed64.zero(),
            )

        next_magnetic = self._read_fixed(proposed, current, "magnetic_field", default="1")
        next_fusion = self._read_fixed(proposed, current, "fusion_rate", default="0")

        computed_collapse = collapse_probability_v1(next_entropy, next_magnetic, next_fusion)

        declared_collapse = self._read_fixed(
            proposed,
            {"collapse_probability": computed_collapse},
            "collapse_probability",
            default="0",
        )
        if abs(declared_collapse - computed_collapse) > self.collapse_consistency_tolerance:
            return PolicyGuardDecision(
                allowed=False,
                reason_codes=("COLLAPSE_FORMULA_MISMATCH",),
                computed_collapse_probability=computed_collapse,
            )

        current_state = self._to_global_state(current, fallback_mass=next_mass, fallback_collapse=computed_collapse)
        proposed_state = self._to_global_state(proposed, fallback_mass=next_mass, fallback_collapse=computed_collapse)

        invariant_results = evaluate_global_invariants(current_state, proposed_state, self.limits)
        failed = tuple(sorted({row.reason_code for row in invariant_results if not row.passed}))

        if failed:
            return PolicyGuardDecision(
                allowed=False,
                reason_codes=failed,
                computed_collapse_probability=computed_collapse,
            )

        return PolicyGuardDecision(
            allowed=True,
            reason_codes=("OK",),
            computed_collapse_probability=computed_collapse,
        )

    def validate_transition(self, current: Mapping[str, Any], proposed: Mapping[str, Any]) -> None:
        decision = self.evaluate_transition(current, proposed)
        if not decision.allowed:
            reasons = ",".join(decision.reason_codes)
            raise ValueError(f"policy_guard: transition rejected ({reasons})")

    @staticmethod
    def _to_fixed(value: Any) -> Fixed64:
        if isinstance(value, Fixed64):
            return value
        if isinstance(value, int):
            return Fixed64.from_int(value)
        if isinstance(value, float):
            # Deterministic decimal rendering for float ingress boundary.
            return Fixed64.from_str(format(value, ".18g"))
        if isinstance(value, str):
            return Fixed64.from_str(value)
        raise TypeError(f"unsupported numeric type: {type(value)!r}")

    def _read_fixed(
        self,
        primary: Mapping[str, Any],
        secondary: Mapping[str, Any],
        key: str,
        *,
        default: str,
    ) -> Fixed64:
        if key in primary:
            return self._to_fixed(primary[key])
        if key in secondary:
            return self._to_fixed(secondary[key])
        return Fixed64.from_str(default)

    def _to_global_state(
        self,
        payload: Mapping[str, Any],
        *,
        fallback_mass: Fixed64,
        fallback_collapse: Fixed64,
    ) -> GlobalState:
        capital = self._to_fixed(payload.get("capital_total", payload.get("mass", fallback_mass)))
        entropy = self._to_fixed(payload.get("entropy_index", "0"))
        collapse = self._to_fixed(payload.get("collapse_probability", fallback_collapse))
        leverage = self._to_fixed(payload.get("leverage_ratio", "0"))
        contagion = self._to_fixed(payload.get("contagion_index", "0"))
        return GlobalState(
            capital_total=capital,
            entropy_index=entropy,
            collapse_probability=collapse,
            leverage_ratio=leverage,
            contagion_index=contagion,
        )
