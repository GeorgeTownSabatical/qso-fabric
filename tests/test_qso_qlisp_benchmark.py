from __future__ import annotations

from tools.qso_qlisp_benchmark import run_benchmarks


def test_quantum_lisp_benchmark_payload_shape() -> None:
    payload = run_benchmarks(iterations=1)
    assert payload["engine"] == "qso.quantum_lisp"
    assert len(payload["results"]) == 4
    assert {row["name"] for row in payload["results"]} == {
        "compile_ir",
        "persisted_analyze",
        "replay_trace",
        "compile_analyze_replay",
    }
