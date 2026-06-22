from __future__ import annotations

from api.mcp_tools.qso_tools import QSOMCPTools
from services.quantum.backends import PennyLaneBackend
from services.quantum.models import QuantumJob
from services.runtime import QSOFabricRuntime


SOURCE = """
(defintent demo.intent :priority 0.9 :confidence 0.8 "stabilize reasoning")
(observe obs.memory :source qso://memory/demo :basis ("claim" "context"))
(hypothesis hyp.bridge obs.memory)
(entangle obs.memory hyp.bridge :kind dependency :weight 0.7)
(project future.bridge :horizon 3 :using (qiskit pennylane cirq itensor))
(reason :goal demo.intent :return ranked-paths)
"""


def test_quantum_lisp_manager_analyze_roundtrip() -> None:
    runtime = QSOFabricRuntime()
    tools = QSOMCPTools(runtime)
    uri = "qso://quantum.state/qlisp_test"
    tools.qso_quantum_create(
        uri=uri,
        payload={
            "object_kind": "quantum_lisp_program",
            "backend": "quantum_lisp",
            "source": SOURCE,
            "verification_hash": "0" * 64,
        },
    )
    out = tools.qso_quantum_lisp_analyze(uri)
    result = out["result"]
    assert result["status"] == "completed"
    assert result["fabric_report"]["patch_count"] >= 2
    assert {row["backend"] for row in result["backend_reports"]} == {"qiskit", "pennylane", "cirq", "itensor"}
    assert len(result["verification_hash"]) == 64

    replay = tools.qso_quantum_lisp_replay(uri)
    assert replay["uri"] == uri
    assert replay["state"]["reasoning_report"]["status"] == "completed"


def test_pennylane_backend_has_deterministic_fallback_shape() -> None:
    result = PennyLaneBackend().execute(
        QuantumJob(
            uri="qso://quantum.state/pennylane_test",
            backend="pennylane",
            qubit_count=2,
            circuit_spec={"gates": [{"name": "h", "target": 0}, {"name": "cnot", "control": 0, "target": 1}]},
            measurement_schema={"shots": 128},
        )
    )
    assert result.backend == "pennylane"
    assert result.status == "completed"
    assert len(result.verification_hash) == 64
