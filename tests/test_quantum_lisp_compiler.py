from __future__ import annotations

import pytest

from services.quantum_lisp import QuantumLispCompiler, parse_quantum_lisp
from services.quantum_lisp.compiler import QuantumLispCompileError


SOURCE = """
(defintent demo.intent :priority 0.9 :confidence 0.8 "stabilize reasoning")
(observe obs.memory :source qso://memory/demo :basis ("claim" "context"))
(hypothesis hyp.bridge obs.memory)
(entangle obs.memory hyp.bridge :kind dependency :weight 0.7)
(project future.bridge :horizon 3 :using (qiskit pennylane cirq itensor))
(reason :goal demo.intent :return ranked-paths)
"""


def test_parse_quantum_lisp_is_deterministic() -> None:
    left = parse_quantum_lisp(SOURCE)
    right = parse_quantum_lisp(SOURCE)
    assert left.ast_hash == right.ast_hash
    assert left.forms[0][0] == "defintent"


def test_compile_quantum_lisp_declares_backends_and_hashes() -> None:
    compiled = QuantumLispCompiler().compile(SOURCE).to_json_dict()
    assert compiled["version"] == "1.0"
    assert len(compiled["ir_hash"]) == 64
    assert compiled["backend_targets"] == ["cirq", "itensor", "pennylane", "qiskit"]
    assert "propose" in compiled["declared_effects"]


def test_compile_rejects_commit_boundary() -> None:
    with pytest.raises(QuantumLispCompileError):
        QuantumLispCompiler().compile("(commit qso://quantum.state/demo)")
