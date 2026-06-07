from __future__ import annotations

from services.quantum.backends.base import QuantumBackend
from services.quantum.models import QuantumExecutionResult, QuantumJob
from solis.shared.hashing import sha256_hex_obj


class QiskitBackend(QuantumBackend):
    name = "qiskit"

    def execute(self, job: QuantumJob) -> QuantumExecutionResult:
        seed_hash = sha256_hex_obj({"backend": self.name, "uri": job.uri, "circuit": job.circuit_spec})
        measurement = {"bitstring": seed_hash[: min(job.qubit_count, 32)], "shots": 1024}
        noise = {"model": "depolarizing", "p": 0.001}
        proof = {"backend": self.name, "job_uri": job.uri, "seed": seed_hash[:24]}
        return QuantumExecutionResult(
            backend=self.name,
            status="completed",
            measurement_results=measurement,
            noise_profile=noise,
            execution_proof=proof,
            verification_hash=sha256_hex_obj({"measurement": measurement, "proof": proof}),
        )
