from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class QuantumJob:
    uri: str
    backend: str
    qubit_count: int
    circuit_spec: dict[str, Any]
    measurement_schema: dict[str, Any]
    policy_version: str = "v1"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QuantumExecutionResult:
    backend: str
    status: str
    measurement_results: dict[str, Any]
    noise_profile: dict[str, Any]
    execution_proof: dict[str, Any]
    verification_hash: str


@dataclass(slots=True)
class QuantumNetworkChannel:
    channel_id: str
    fidelity: float
    routing_latency_ms: float
    entanglement_generation_rate: float
