from __future__ import annotations

from services.quantum.models import QuantumExecutionResult, QuantumJob
from services.quantum.backends.qiskit_backend import QiskitBackend
from solis.shared.hashing import sha256_hex_obj


class CirqBackend(QiskitBackend):
    name = "cirq"

    def execute(self, job: QuantumJob) -> QuantumExecutionResult:
        try:
            import cirq  # type: ignore[import-not-found]
        except Exception:
            return self._fallback(job)

        qubits = [cirq.LineQubit(index) for index in range(job.qubit_count)]
        circuit = cirq.Circuit()
        for gate in list(job.circuit_spec.get("gates", [])):
            name = str(gate.get("name", "")).strip().lower()
            if name == "h":
                circuit.append(cirq.H(qubits[int(gate["target"])]))
            elif name == "x":
                circuit.append(cirq.X(qubits[int(gate["target"])]))
            elif name == "z":
                circuit.append(cirq.Z(qubits[int(gate["target"])]))
            elif name in {"cnot", "cx"}:
                circuit.append(cirq.CNOT(qubits[int(gate["control"])], qubits[int(gate["target"])]))
        circuit.append(cirq.measure(*qubits, key="m"))
        shots = int(job.measurement_schema.get("shots", 1024))
        result = cirq.Simulator().run(circuit, repetitions=shots)
        counts = {str(key): int(value) for key, value in result.histogram(key="m").items()}
        measurement = {"counts": counts, "shots": shots}
        proof = {"backend": self.name, "job_uri": job.uri, "engine": "cirq_simulator", "circuit_hash": sha256_hex_obj(job.circuit_spec)}
        return QuantumExecutionResult(
            backend=self.name,
            status="completed",
            measurement_results=measurement,
            noise_profile={"model": "ideal_cirq_simulator"},
            execution_proof=proof,
            verification_hash=sha256_hex_obj({"measurement": measurement, "proof": proof}),
        )
