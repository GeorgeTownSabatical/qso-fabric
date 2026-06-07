from __future__ import annotations

from typing import Any, Protocol

from solis.config import SolisConfig


class GateHealthRollupQSO(Protocol):
    def create(self, uri: str, schema: dict[str, Any]) -> dict[str, Any]: ...

    def has(self, uri: str) -> bool: ...

    def timeline(self, uri: str, strict: bool = True) -> list[dict[str, Any]]: ...

    def patch(
        self,
        uri: str,
        delta: dict[str, Any],
        *,
        actor: str,
        policy_version: str,
        node_id: str,
    ) -> dict[str, Any]: ...


def emit_gate_health_rollup(
    *,
    qso: GateHealthRollupQSO,
    config: SolisConfig,
    scope: str,
    actor: str = "solis.gate.health",
) -> str:
    source_prefix = f"qso://solis.gate.{scope}."
    health_uri = f"qso://solis.gate.health.{scope}"
    decision_uris = _decision_uris(qso, source_prefix)

    pass_count = 0
    fail_count = 0
    gate_counts: dict[str, dict[str, int]] = {}
    stage_counts: dict[str, dict[str, int]] = {}

    for uri in decision_uris:
        for event in qso.timeline(uri, strict=True):
            delta = event.get("delta", {})
            if not isinstance(delta, dict):
                continue
            if str(delta.get("scope", "")).strip() != scope:
                continue

            passed = bool(delta.get("passed", False))
            if passed:
                pass_count += 1
            else:
                fail_count += 1

            gate = str(delta.get("gate", "")).strip() or "unknown"
            stage = str(delta.get("stage", "")).strip() or "unknown"
            _increment(gate_counts, gate, passed)
            _increment(stage_counts, stage, passed)

    total_count = pass_count + fail_count
    payload = {
        "scope": scope,
        "source_prefix": source_prefix,
        "decision_uri_count": len(decision_uris),
        "decision_event_count": total_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": _rate(pass_count, total_count),
        "fail_rate": _rate(fail_count, total_count),
        "ordered_gate_decision_uris": decision_uris,
        "by_gate": _ordered_breakdown(gate_counts, "gate"),
        "by_stage": _ordered_breakdown(stage_counts, "stage"),
    }

    if not qso.has(health_uri):
        qso.create(health_uri, {"type": "solis_gate_health", "scope": scope})
    qso.patch(
        health_uri,
        payload,
        actor=actor,
        policy_version=config.policy_version,
        node_id=config.node_id,
    )
    return health_uri


def _decision_uris(qso: GateHealthRollupQSO, source_prefix: str) -> list[str]:
    tools = getattr(qso, "tools", None)
    runtime = getattr(tools, "runtime", None)
    registry = getattr(runtime, "registry", None)
    list_uris = getattr(registry, "list_uris", None)
    if not callable(list_uris):
        return []
    return sorted([uri for uri in list_uris() if str(uri).startswith(source_prefix)])


def _increment(counter: dict[str, dict[str, int]], key: str, passed: bool) -> None:
    row = counter.setdefault(key, {"pass_count": 0, "fail_count": 0})
    if passed:
        row["pass_count"] += 1
    else:
        row["fail_count"] += 1


def _ordered_breakdown(counter: dict[str, dict[str, int]], label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(counter.keys()):
        pass_count = int(counter[key]["pass_count"])
        fail_count = int(counter[key]["fail_count"])
        total_count = pass_count + fail_count
        rows.append(
            {
                label: key,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "total_count": total_count,
                "pass_rate": _rate(pass_count, total_count),
                "fail_rate": _rate(fail_count, total_count),
            }
        )
    return rows


def _rate(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total, 12)
