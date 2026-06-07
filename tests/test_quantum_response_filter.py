from __future__ import annotations

from services.quantum.response_filter import QuantumResponseFilter


def test_quantum_response_filter_creates_qso_execution_envelope() -> None:
    response_filter = QuantumResponseFilter(backend="itensor", max_qubits=4)
    payload = {
        "uri": "qso://sandbox/demo/conversation/main",
        "conversation_id": "main",
        "messages": [
            {"author": "user", "role": "user", "content": "hello"},
            {"author": "assistant", "role": "assistant", "content": "world"},
        ],
    }
    out = response_filter.filter_payload(payload, conversation_id="main", phase="lower_bound")
    assert out["backend"] == "itensor"
    assert out["phase"] == "lower_bound"
    assert out["uri"].startswith("qso://quantum.state/filter/")
    assert out["result"]["status"] == "completed"
    assert "logical_entanglement_graph" in out["result"]["measurement_results"]
