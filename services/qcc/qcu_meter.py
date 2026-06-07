from __future__ import annotations

from typing import Any, Mapping


class QCUMeter:
    def estimate(self, job: Mapping[str, Any]) -> dict[str, float]:
        qubits = max(1, int(job.get("qubit_count", 1)))
        depth = max(1, int(job.get("depth", 1)))
        shots = max(1, int(job.get("shots", 1024)))

        qcu = (qubits * depth * shots) / 1_000_000.0
        return {
            "qcu": round(qcu, 8),
            "qubits": float(qubits),
            "depth": float(depth),
            "shots": float(shots),
        }
