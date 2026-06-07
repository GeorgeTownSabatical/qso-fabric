from __future__ import annotations

from services.quantum.backends import ITensorBackend
from services.quantum.models import QuantumJob


def test_itensor_backend_fallback_simulates_bell_pair() -> None:
    backend = ITensorBackend(runner_path="")
    job = QuantumJob(
        uri="qso://quantum.state/test_bell",
        backend="itensor",
        qubit_count=2,
        circuit_spec={"gates": [{"name": "h", "target": 0}, {"name": "cnot", "control": 0, "target": 1}]},
        measurement_schema={"shots": 128},
    )
    result = backend.execute(job)
    counts = result.measurement_results["counts"]
    assert set(counts) == {"00", "11"}
    assert result.execution_proof["engine"] == "builtin_statevector_fallback"
    assert result.execution_proof["requested_backend"] == "itensor"
