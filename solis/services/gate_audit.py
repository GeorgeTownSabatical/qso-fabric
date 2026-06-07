from __future__ import annotations

from typing import Any, Mapping, Protocol

from solis.config import SolisConfig
from solis.integration.gates import GateResult
from solis.services.gate_health_rollup import emit_gate_health_rollup
from solis.shared.hashing import sha256_hex_obj


class GateAuditQSO(Protocol):
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


def emit_gate_decision(
    *,
    qso: GateAuditQSO,
    config: SolisConfig,
    scope: str,
    stage: str,
    target_uri: str,
    gate: GateResult,
    actor: str = "solis.gate",
    context: Mapping[str, Any] | None = None,
) -> str:
    base_material = {
        "scope": scope,
        "stage": stage,
        "target_uri": target_uri,
        "gate": gate.gate,
    }
    decision_id = sha256_hex_obj(base_material)[:24]
    uri = f"qso://solis.gate.{scope}.{decision_id}"

    if not qso.has(uri):
        qso.create(uri, {"type": "solis_gate_decision"})

    payload = {
        "scope": scope,
        "stage": stage,
        "target_uri": target_uri,
        "gate": gate.gate,
        "passed": gate.passed,
        "detail": gate.detail,
        "context_hash": sha256_hex_obj(dict(context or {})),
    }
    qso.patch(
        uri,
        payload,
        actor=actor,
        policy_version=config.policy_version,
        node_id=config.node_id,
    )
    emit_gate_health_rollup(
        qso=qso,
        config=config,
        scope=scope,
    )
    return uri
