from __future__ import annotations

import argparse
import json
from pathlib import Path

from api.mcp_tools.qso_tools import QSOMCPTools


DEMO_SOURCE = """
(defintent demo.intent :priority 0.9 :confidence 0.8 "stabilize reasoning")
(observe obs.memory :source qso://memory/demo :basis ("claim" "context"))
(hypothesis hyp.bridge obs.memory)
(entangle obs.memory hyp.bridge :kind dependency :weight 0.7)
(project future.bridge :horizon 3 :using (qiskit pennylane cirq itensor))
(reason :goal demo.intent :return ranked-paths)
"""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile and analyze QSO Quantum LISP programs")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_cmd = sub.add_parser("compile")
    compile_cmd.add_argument("source_path")
    analyze_cmd = sub.add_parser("analyze")
    analyze_cmd.add_argument("source_path")
    analyze_cmd.add_argument("--uri", default="qso://quantum.state/qlisp_cli")
    sub.add_parser("demo")
    return parser


def _read_source(path: str) -> str:
    return DEMO_SOURCE if path == "-" else Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    tools = QSOMCPTools()
    if args.command == "demo":
        source = DEMO_SOURCE
        uri = "qso://quantum.state/qlisp_demo"
        tools.qso_quantum_create(uri=uri, payload={"object_kind": "quantum_lisp_program", "backend": "quantum_lisp", "source": source, "verification_hash": "0" * 64})
        print(json.dumps(tools.qso_quantum_lisp_analyze(uri), indent=2, sort_keys=True))
        return
    source = _read_source(args.source_path)
    if args.command == "compile":
        print(json.dumps(tools.qso_quantum_lisp_compile(source), indent=2, sort_keys=True))
        return
    tools.qso_quantum_create(uri=args.uri, payload={"object_kind": "quantum_lisp_program", "backend": "quantum_lisp", "source": source, "verification_hash": "0" * 64})
    print(json.dumps(tools.qso_quantum_lisp_analyze(args.uri), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
