from __future__ import annotations

from services.quantum.backends.base import QuantumBackend
from services.quantum.models import QuantumExecutionResult, QuantumJob
from services.quantum.simulators import simulate_quantum_job
from solis.shared.hashing import sha256_hex_obj


class PennyLaneBackend(QuantumBackend):
    name = "pennylane"

    def execute(self, job: QuantumJob) -> QuantumExecutionResult:
        try:
            import pennylane as qml  # type: ignore[import-not-found]
        except Exception:
            payload = simulate_quantum_job(job)
            proof = {
                **dict(payload["execution_proof"]),
                "requested_backend": self.name,
                "pennylane_available": False,
                "reason": "pennylane_import_unavailable",
            }
            measurement = dict(payload["measurement_results"])
            noise = dict(payload["noise_profile"])
            return QuantumExecutionResult(
                backend=self.name,
                status="completed",
                measurement_results=measurement,
                noise_profile=noise,
                execution_proof=proof,
                verification_hash=sha256_hex_obj({"measurement": measurement, "proof": proof}),
            )

        dev = qml.device("default.qubit", wires=job.qubit_count, shots=None)

        @qml.qnode(dev)
        def circuit() -> list[float]:
            for gate in list(job.circuit_spec.get("gates", [])):
                name = str(gate.get("name", "")).strip().lower()
                if name == "h":
                    qml.Hadamard(wires=int(gate["target"]))
                elif name == "x":
                    qml.PauliX(wires=int(gate["target"]))
                elif name == "z":
                    qml.PauliZ(wires=int(gate["target"]))
                elif name in {"cnot", "cx"}:
                    qml.CNOT(wires=[int(gate["control"]), int(gate["target"])])
            return [qml.expval(qml.PauliZ(wire)) for wire in range(job.qubit_count)]

        expectations = [round(float(value), 8) for value in circuit()]
        measurement = {"expectation_z": expectations, "shots": job.measurement_schema.get("shots", 0)}
        proof = {
            "engine": "pennylane_default_qubit",
            "gate_count": len(list(job.circuit_spec.get("gates", []))),
            "circuit_hash": sha256_hex_obj(job.circuit_spec),
            "pennylane_available": True,
        }
        return QuantumExecutionResult(
            backend=self.name,
            status="completed",
            measurement_results=measurement,
            noise_profile={"model": "ideal_default_qubit", "backend": self.name},
            execution_proof=proof,
            verification_hash=sha256_hex_obj({"measurement": measurement, "proof": proof}),
        )
