# Quantum LISP Benchmark Report

- Generated: `2026-06-22T04:53:51.369556+00:00`
- Engine: `qso.quantum_lisp`
- Iterations: `25`
- Python: `3.14.3`
- Platform: `macOS-26.3-x86_64-i386-64bit-Mach-O`
- Source hash: `16995acdd89c12089812824529a3bdf61e4e8eccebe437ac606f0d76a42368e0`
- IR hash: `7b69b3f41181d4ce1652442771f1003b7bd492c0c96818d093fc7b2aaa0d3d93`
- Backend targets: `cirq, itensor, pennylane, qiskit`

| Benchmark | Iterations | Total ms | Mean ms | P50 ms | P95 ms | Min ms | Max ms | Ops/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `compile_ir` | 25 | 6.186 | 0.2474 | 0.2377 | 0.3409 | 0.1782 | 0.4166 | 4041.39 |
| `persisted_analyze` | 25 | 91.4509 | 3.658 | 3.4877 | 4.9121 | 2.9906 | 5.0928 | 273.37 |
| `replay_trace` | 25 | 14.8001 | 0.592 | 0.5479 | 0.8934 | 0.4113 | 0.9113 | 1689.18 |
| `compile_analyze_replay` | 25 | 91.9779 | 3.6791 | 3.6441 | 4.3018 | 3.0755 | 4.7608 | 271.8 |

Benchmarks use the built-in Quantum LISP demo source and the local deterministic backend fallbacks when native quantum libraries are unavailable.
