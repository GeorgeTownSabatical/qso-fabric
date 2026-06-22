from __future__ import annotations

from typing import Any

from services.event_log.service import EventLogService
from services.quantum.backends import CirqBackend, ITensorBackend, PennyLaneBackend, PhotonicBackend, QiskitBackend, QuantumBackend, RemoteGrpcBackend
from services.quantum.fabric.runtime import execute_fabric_payload
from services.quantum.models import QuantumExecutionResult, QuantumJob
from services.state_engine.service import StateEngineService
from solis.shared.hashing import sha256_hex_obj


class QuantumManager:
    def __init__(self, *, state_engine: StateEngineService, event_log: EventLogService) -> None:
        self.state_engine = state_engine
        self.event_log = event_log
        self.backends: dict[str, QuantumBackend] = {}
        self.register_default_backends()

    def register_backend(self, backend: QuantumBackend) -> None:
        self.backends[backend.name] = backend

    def register_default_backends(self) -> None:
        for backend in (QiskitBackend(), CirqBackend(), PennyLaneBackend(), PhotonicBackend(), RemoteGrpcBackend(), ITensorBackend()):
            self.register_backend(backend)

    def execute(self, *, uri: str, actor: str = "quantum-manager", policy_version: str = "v1", node_id: str = "local") -> dict[str, Any]:
        obj = self.state_engine.read(uri)
        payload = dict(obj.state_layer)
        object_kind = str(payload.get("object_kind", "")).strip().lower()
        if object_kind == "fabric" or "fabric_payload" in payload:
            fabric_result = execute_fabric_payload(
                payload,
                coherence_threshold=float(payload.get("coherence_threshold", 0.8)),
            )
            delta = {
                "execution": {
                    "backend": "fabric_gluing",
                    "status": "completed",
                    "measurement_results": {
                        "global_coherence": fabric_result["global_coherence"],
                        "obstruction_score": fabric_result["obstruction_score"],
                        "healthy": fabric_result["healthy"],
                    },
                    "noise_profile": {"model": "deterministic_fabric_analysis"},
                    "execution_proof": {
                        "engine": "fabric_gluing",
                        "fabric_id": fabric_result["fabric_id"],
                        "patch_count": fabric_result["patch_count"],
                        "overlap_count": fabric_result["overlap_count"],
                    },
                    "verification_hash": sha256_hex_obj({"uri": uri, "fabric_result": fabric_result}),
                    "state_hash": sha256_hex_obj({"uri": uri, "fabric": fabric_result}),
                    "fabric_report": fabric_result,
                }
            }
            event = self.state_engine.patch(
                uri=uri,
                delta=delta,
                actor=actor,
                policy_version=policy_version,
                node_id=node_id,
            )
            return {
                "event": event.model_dump(mode="json"),
                "result": {
                    "backend": "fabric_gluing",
                    "status": "completed",
                    "measurement_results": delta["execution"]["measurement_results"],
                    "noise_profile": delta["execution"]["noise_profile"],
                    "execution_proof": delta["execution"]["execution_proof"],
                    "verification_hash": delta["execution"]["verification_hash"],
                    "fabric_report": fabric_result,
                },
            }
        backend_name = str(payload.get("backend", "qiskit"))
        backend = self.backends.get(backend_name)
        if backend is None:
            raise ValueError(f"unknown quantum backend: {backend_name}")

        job = QuantumJob(
            uri=uri,
            backend=backend_name,
            qubit_count=int(payload.get("qubit_count", 1)),
            circuit_spec=dict(payload.get("circuit_spec", {})),
            measurement_schema=dict(payload.get("measurement_schema", {})),
            policy_version=policy_version,
            metadata=dict(payload.get("metadata", {})),
        )

        result = backend.execute(job)
        delta = {
            "execution": {
                "backend": result.backend,
                "status": result.status,
                "measurement_results": result.measurement_results,
                "noise_profile": result.noise_profile,
                "execution_proof": result.execution_proof,
                "verification_hash": result.verification_hash,
                "state_hash": sha256_hex_obj({"uri": uri, "result": result.measurement_results}),
            }
        }
        event = self.state_engine.patch(
            uri=uri,
            delta=delta,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        return {
            "event": event.model_dump(mode="json"),
            "result": {
                "backend": result.backend,
                "status": result.status,
                "measurement_results": result.measurement_results,
                "noise_profile": result.noise_profile,
                "execution_proof": result.execution_proof,
                "verification_hash": result.verification_hash,
            },
        }


def summarize_quantum_result(result: QuantumExecutionResult) -> dict[str, Any]:
    return {
        "backend": result.backend,
        "status": result.status,
        "verification_hash": result.verification_hash,
    }
