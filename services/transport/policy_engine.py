from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping

from services.transport.models import TransportMode

DEFAULT_TRANSPORT_POLICY: dict[str, list[str]] = {
    "research": [TransportMode.DIRECT.value, TransportMode.VPN.value, TransportMode.TOR.value],
    "model_training": [TransportMode.DIRECT.value, TransportMode.VPN.value],
    "market_execution": [TransportMode.DIRECT.value, TransportMode.VPN.value],
    "identity_binding": [TransportMode.DIRECT.value],
    "transport_control": [TransportMode.DIRECT.value, TransportMode.VPN.value, TransportMode.TOR.value],
}


@dataclass(slots=True)
class TransportPolicyEngine:
    policy: dict[str, list[str]]
    version: str = "v1"

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, object] | None = None,
        *,
        default_version: str = "v1",
    ) -> "TransportPolicyEngine":
        raw = payload or {}
        raw_policy = raw.get("policy", raw)
        if not isinstance(raw_policy, Mapping):
            raw_policy = DEFAULT_TRANSPORT_POLICY

        normalized: dict[str, list[str]] = {}
        for workload, allowed in dict(raw_policy).items():
            if isinstance(allowed, (list, tuple, set)):
                modes = [str(item).strip().lower() for item in allowed if str(item).strip()]
            else:
                modes = []
            if not modes:
                modes = [TransportMode.DIRECT.value]
            normalized[str(workload)] = sorted(set(modes))

        if "transport_control" not in normalized:
            normalized["transport_control"] = [
                TransportMode.DIRECT.value,
                TransportMode.VPN.value,
                TransportMode.TOR.value,
            ]

        raw_version = str(raw.get("version", default_version)).strip() or default_version
        return cls(policy=normalized, version=raw_version)

    def allows(self, workload_type: str, mode: TransportMode | str) -> bool:
        normalized_workload = str(workload_type).strip() or "research"
        normalized_mode = str(mode.value if isinstance(mode, TransportMode) else mode).strip().lower()
        allowed = self.policy.get(normalized_workload)
        if allowed is None:
            # Fail closed: unknown workloads inherit the safest default (no Tor).
            allowed = self.policy.get("model_training", [TransportMode.DIRECT.value])
        return normalized_mode in allowed

    def enforce(self, workload_type: str, mode: TransportMode | str) -> None:
        if not self.allows(workload_type, mode):
            normalized_mode = str(mode.value if isinstance(mode, TransportMode) else mode)
            raise PermissionError(
                f"transport mode '{normalized_mode}' is not allowed for workload '{workload_type}'"
            )

    def allowed_modes(self, workload_type: str) -> list[str]:
        return list(self.policy.get(workload_type, []))

    def export(self) -> dict[str, object]:
        return {
            "version": self.version,
            "policy": deepcopy(self.policy),
        }
