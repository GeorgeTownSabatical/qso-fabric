from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class GovernanceInvariantResult:
    name: str
    passed: bool
    reason_code: str
    detail: str = ""


@dataclass(frozen=True)
class GovernanceInvariantLimits:
    max_gross_exposure_bps: int = 20_000
    max_net_exposure_bps: int = 10_000
    max_single_name_exposure_bps: int = 5_000
    max_turnover_bps_per_horizon: int = 15_000
    min_liquidity_score: float = 0.05
    max_volatility_score: float = 1.00
    max_regime_uncertainty: float = 1.00


@dataclass(frozen=True)
class GovernanceInvariantContext:
    projected_gross_exposure_bps: int
    projected_net_exposure_bps: int
    projected_single_name_exposure_bps: int
    projected_turnover_bps: int
    liquidity_score: float
    volatility_score: float
    regime_uncertainty: float
    kill_switch_active: bool
    pause_switch_active: bool
    venue_healthy: bool


def _ok(name: str) -> GovernanceInvariantResult:
    return GovernanceInvariantResult(name=name, passed=True, reason_code="OK")


def _fail(name: str, reason_code: str, detail: str = "") -> GovernanceInvariantResult:
    return GovernanceInvariantResult(name=name, passed=False, reason_code=reason_code, detail=detail)


def _to_int(value: Any, *, default: int) -> int:
    if value is None:
        return int(default)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    text = str(value).strip()
    if not text:
        return int(default)
    return int(round(float(text)))


def _to_float(value: Any, *, default: float) -> float:
    if value is None:
        return float(default)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip()
    if not text:
        return float(default)
    return float(text)


def _to_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off"}:
        return False
    return bool(default)


def governance_context_from_transition(
    current: Mapping[str, Any],
    proposed: Mapping[str, Any],
) -> GovernanceInvariantContext:
    current_gross = _to_int(current.get("gross_exposure_bps"), default=0)
    current_net = _to_int(current.get("net_exposure_bps"), default=0)
    current_single = _to_int(current.get("single_name_exposure_bps"), default=0)
    current_turnover = _to_int(current.get("turnover_bps_in_horizon"), default=0)
    requested_delta = _to_int(
        proposed.get(
            "requested_exposure_delta_bps",
            proposed.get("exposure_delta_bps"),
        ),
        default=0,
    )

    projected_gross = _to_int(
        proposed.get("gross_exposure_bps"),
        default=current_gross + abs(requested_delta),
    )
    projected_net = _to_int(
        proposed.get("net_exposure_bps"),
        default=current_net + requested_delta,
    )
    projected_single = _to_int(
        proposed.get("single_name_exposure_bps"),
        default=abs(current_single + requested_delta),
    )
    projected_turnover = _to_int(
        proposed.get("turnover_bps_in_horizon"),
        default=current_turnover + abs(requested_delta),
    )

    liquidity_score = _to_float(proposed.get("liquidity_score", current.get("liquidity_score")), default=1.0)
    volatility_score = _to_float(
        proposed.get("volatility_score", current.get("volatility_score")),
        default=0.0,
    )
    regime_uncertainty = _to_float(
        proposed.get("regime_uncertainty", current.get("regime_uncertainty")),
        default=0.0,
    )
    kill_switch_active = _to_bool(
        proposed.get("kill_switch_active", current.get("kill_switch_active")),
        default=False,
    )
    pause_switch_active = _to_bool(
        proposed.get("pause_switch_active", current.get("pause_switch_active")),
        default=False,
    )
    venue_healthy = _to_bool(
        proposed.get("venue_healthy", current.get("venue_healthy")),
        default=True,
    )

    return GovernanceInvariantContext(
        projected_gross_exposure_bps=projected_gross,
        projected_net_exposure_bps=projected_net,
        projected_single_name_exposure_bps=projected_single,
        projected_turnover_bps=projected_turnover,
        liquidity_score=liquidity_score,
        volatility_score=volatility_score,
        regime_uncertainty=regime_uncertainty,
        kill_switch_active=kill_switch_active,
        pause_switch_active=pause_switch_active,
        venue_healthy=venue_healthy,
    )


def evaluate_governance_invariants(
    context: GovernanceInvariantContext,
    limits: GovernanceInvariantLimits,
) -> list[GovernanceInvariantResult]:
    rows: list[GovernanceInvariantResult] = []

    if context.kill_switch_active:
        rows.append(_fail("kill_switch", "KILL_SWITCH_ACTIVE"))
    else:
        rows.append(_ok("kill_switch"))

    if context.pause_switch_active:
        rows.append(_fail("pause_switch", "PAUSE_SWITCH_ACTIVE"))
    else:
        rows.append(_ok("pause_switch"))

    if not context.venue_healthy:
        rows.append(_fail("venue_health", "VENUE_UNHEALTHY"))
    else:
        rows.append(_ok("venue_health"))

    if context.projected_gross_exposure_bps > limits.max_gross_exposure_bps:
        rows.append(
            _fail(
                "gross_exposure",
                "GROSS_EXPOSURE_LIMIT_EXCEEDED",
                detail=f"{context.projected_gross_exposure_bps}>{limits.max_gross_exposure_bps}",
            )
        )
    else:
        rows.append(_ok("gross_exposure"))

    if abs(context.projected_net_exposure_bps) > limits.max_net_exposure_bps:
        rows.append(
            _fail(
                "net_exposure",
                "NET_EXPOSURE_LIMIT_EXCEEDED",
                detail=f"{abs(context.projected_net_exposure_bps)}>{limits.max_net_exposure_bps}",
            )
        )
    else:
        rows.append(_ok("net_exposure"))

    if context.projected_single_name_exposure_bps > limits.max_single_name_exposure_bps:
        rows.append(
            _fail(
                "single_name_exposure",
                "SINGLE_NAME_EXPOSURE_LIMIT_EXCEEDED",
                detail=(
                    f"{context.projected_single_name_exposure_bps}"
                    f">{limits.max_single_name_exposure_bps}"
                ),
            )
        )
    else:
        rows.append(_ok("single_name_exposure"))

    if context.projected_turnover_bps > limits.max_turnover_bps_per_horizon:
        rows.append(
            _fail(
                "turnover",
                "TURNOVER_LIMIT_EXCEEDED",
                detail=f"{context.projected_turnover_bps}>{limits.max_turnover_bps_per_horizon}",
            )
        )
    else:
        rows.append(_ok("turnover"))

    if context.liquidity_score < limits.min_liquidity_score:
        rows.append(
            _fail(
                "liquidity",
                "LIQUIDITY_BELOW_MINIMUM",
                detail=f"{context.liquidity_score:.6f}<{limits.min_liquidity_score:.6f}",
            )
        )
    else:
        rows.append(_ok("liquidity"))

    if context.volatility_score > limits.max_volatility_score:
        rows.append(
            _fail(
                "volatility",
                "VOLATILITY_ABOVE_MAX",
                detail=f"{context.volatility_score:.6f}>{limits.max_volatility_score:.6f}",
            )
        )
    else:
        rows.append(_ok("volatility"))

    if context.regime_uncertainty > limits.max_regime_uncertainty:
        rows.append(
            _fail(
                "regime_uncertainty",
                "REGIME_UNCERTAINTY_ABOVE_MAX",
                detail=f"{context.regime_uncertainty:.6f}>{limits.max_regime_uncertainty:.6f}",
            )
        )
    else:
        rows.append(_ok("regime_uncertainty"))

    return rows
