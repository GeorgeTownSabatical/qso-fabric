from __future__ import annotations

from typing import Any

from solis.shared.hashing import sha256_hex_obj

from services.quantum_lisp.models import QuantumReasoningIR
from services.quantum_lisp.parser import parse_quantum_lisp

ALLOWED_FORMS = {"defintent", "observe", "hypothesis", "entangle", "contradict", "repair", "project", "trust", "algebra", "reason"}
FORBIDDEN_FORMS = {"commit", "measure-state", "clone-state", "postselect"}
ALLOWED_BACKENDS = {"qiskit", "pennylane", "cirq", "itensor", "fabric_gluing"}


class QuantumLispCompileError(ValueError):
    pass


def _pairs(items: list[Any]) -> tuple[list[Any], dict[str, Any]]:
    positional: list[Any] = []
    options: dict[str, Any] = {}
    index = 0
    while index < len(items):
        item = items[index]
        if isinstance(item, str) and item.startswith(":"):
            if index + 1 >= len(items):
                raise QuantumLispCompileError(f"missing value for option {item}")
            options[item[1:]] = items[index + 1]
            index += 2
            continue
        positional.append(item)
        index += 1
    return positional, options


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


class QuantumLispCompiler:
    version = "1.0"

    def compile(self, source: str, *, metadata: dict[str, Any] | None = None) -> QuantumReasoningIR:
        program = parse_quantum_lisp(source)
        forms: list[dict[str, Any]] = []
        backends: set[str] = set()
        effects = {"read", "analyze", "propose"}

        for raw in program.forms:
            if not raw:
                raise QuantumLispCompileError("empty form")
            op = str(raw[0]).strip().lower()
            if op in FORBIDDEN_FORMS:
                raise QuantumLispCompileError(f"{op} is outside the descriptive Quantum LISP boundary")
            if op not in ALLOWED_FORMS:
                raise QuantumLispCompileError(f"unknown Quantum LISP form: {op}")
            positional, options = _pairs(list(raw[1:]))
            form = {"op": op, "args": positional, "options": options}
            if op == "project":
                requested = set(_as_list(options.get("using")))
                unknown = requested - ALLOWED_BACKENDS
                if unknown:
                    raise QuantumLispCompileError(f"unknown backend target(s): {', '.join(sorted(unknown))}")
                backends.update(requested)
            forms.append(form)

        if not forms:
            raise QuantumLispCompileError("program contains no forms")
        if not backends:
            backends.add("fabric_gluing")

        lineage = {
            "compiler": "qso.quantum_lisp",
            "compiler_version": self.version,
            "metadata": dict(metadata or {}),
        }
        payload = {
            "version": self.version,
            "source_hash": program.source_hash,
            "ast_hash": program.ast_hash,
            "declared_effects": sorted(effects),
            "backend_targets": sorted(backends),
            "forms": forms,
            "lineage": lineage,
        }
        return QuantumReasoningIR(ir_hash=sha256_hex_obj(payload), **payload)
