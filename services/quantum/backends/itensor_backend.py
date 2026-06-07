from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from services.quantum.backends.base import QuantumBackend
from services.quantum.models import QuantumExecutionResult, QuantumJob
from services.quantum.simulators import simulate_quantum_job
from solis.shared.hashing import sha256_hex_obj


class ITensorBackend(QuantumBackend):
    name = "itensor"

    def __init__(self, runner_path: str | None = None) -> None:
        raw_runner = runner_path if runner_path is not None else os.getenv("QSO_ITENSOR_RUNNER", "")
        self.runner_path = str(raw_runner).strip()

    def execute(self, job: QuantumJob) -> QuantumExecutionResult:
        if self.runner_path:
            payload = self._run_external(job)
        else:
            payload = simulate_quantum_job(job)
            payload["execution_proof"] = {
                **dict(payload["execution_proof"]),
                "requested_backend": self.name,
                "itensor_runner_configured": False,
            }

        measurement_results = dict(payload.get("measurement_results", {}))
        noise_profile = dict(payload.get("noise_profile", {}))
        execution_proof = dict(payload.get("execution_proof", {}))
        verification_hash = str(
            payload.get(
                "verification_hash",
                sha256_hex_obj(
                    {
                        "uri": job.uri,
                        "measurement_results": measurement_results,
                        "execution_proof": execution_proof,
                    }
                ),
            )
        )
        return QuantumExecutionResult(
            backend=self.name,
            status=str(payload.get("status", "completed")),
            measurement_results=measurement_results,
            noise_profile=noise_profile,
            execution_proof=execution_proof,
            verification_hash=verification_hash,
        )

    def _run_external(self, job: QuantumJob) -> dict[str, Any]:
        runner_input = {
            "job": {
                "uri": job.uri,
                "backend": job.backend,
                "qubit_count": job.qubit_count,
                "circuit_spec": job.circuit_spec,
                "measurement_schema": job.measurement_schema,
                "policy_version": job.policy_version,
                "metadata": job.metadata,
            }
        }
        proc = subprocess.run(
            [self.runner_path],
            input=json.dumps(runner_input),
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ITensor runner failed with exit code {proc.returncode}: {proc.stderr.strip()}")
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("ITensor runner returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("ITensor runner returned a non-object payload")
        return payload
