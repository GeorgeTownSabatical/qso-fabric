from __future__ import annotations

from typing import Any, Dict, Mapping

from api.mcp_tools.qso_tools import QSOMCPTools


class SolisOptimizer:
    """Deterministic GDML optimization adapter for Solis proposals."""

    def __init__(self, qso: QSOMCPTools | None = None, policy_version: str = "v1", node_id: str = "solis") -> None:
        self.qso = qso or QSOMCPTools()
        self.policy_version = policy_version
        self.node_id = node_id

    def propose(
        self,
        *,
        constellation_uri: str,
        metrics: Mapping[str, float],
        actor: str = "solis.optimizer",
    ) -> Dict[str, Any]:
        domain = constellation_uri.rsplit(".", 1)[-1]
        proposal_uri = f"qso://solis.optimizer.{domain}"

        if not self.qso.runtime.registry.has(proposal_uri):
            self.qso.qso_create(
                proposal_uri,
                {
                    "type": "solis_optimizer_proposal",
                    "constellation_uri": constellation_uri,
                },
            )

        contagion = float(metrics.get("contagion_index", 0.0))
        collapse = float(metrics.get("collapse_mean", 0.0))
        entropy = float(metrics.get("entropy_mean", 0.0))

        proposals = {
            "emission_rate_delta": -0.02 if contagion > 0.6 else 0.01,
            "validator_weight_rebalance": 0.15 if collapse > 0.5 else 0.05,
            "governance_damping_coefficient": min(max(entropy * 0.4, 0.05), 0.85),
        }

        payload = {
            "constellation_uri": constellation_uri,
            "metrics": dict(metrics),
            "proposals": proposals,
        }

        event = self.qso.qso_patch(
            uri=proposal_uri,
            delta=payload,
            actor=actor,
            policy_version=self.policy_version,
            node_id=self.node_id,
        )

        return {
            "uri": proposal_uri,
            "event_id": event["event_id"],
            "proposals": proposals,
        }
