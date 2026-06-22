from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from api.mcp_tools.qso_tools import QSOMCPTools
from tools.qso_qlisp import DEMO_SOURCE


@dataclass(frozen=True, slots=True)
class BenchResult:
    name: str
    iterations: int
    total_ms: float
    mean_ms: float
    p50_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float
    throughput_ops_s: float


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return ordered[low]
    frac = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac


def _bench(name: str, iterations: int, fn: Callable[[int], Any]) -> BenchResult:
    timings: list[float] = []
    for idx in range(iterations):
        start = time.perf_counter()
        fn(idx)
        timings.append((time.perf_counter() - start) * 1000.0)
    total_ms = sum(timings)
    throughput = (iterations / (total_ms / 1000.0)) if total_ms > 0 else 0.0
    return BenchResult(
        name=name,
        iterations=iterations,
        total_ms=round(total_ms, 4),
        mean_ms=round(statistics.fmean(timings), 4),
        p50_ms=round(_percentile(timings, 0.50), 4),
        p95_ms=round(_percentile(timings, 0.95), 4),
        min_ms=round(min(timings), 4),
        max_ms=round(max(timings), 4),
        throughput_ops_s=round(throughput, 2),
    )


def run_benchmarks(*, iterations: int, source: str = DEMO_SOURCE) -> dict[str, Any]:
    tools = QSOMCPTools()
    compiled_cache: dict[str, Any] = {}
    analyze_uris: list[str] = []

    compile_result = _bench("compile_ir", iterations, lambda _idx: tools.qso_quantum_lisp_compile(source))

    def analyze_once(idx: int) -> None:
        uri = f"qso://quantum.state/qlisp_bench_analyze_{idx}"
        tools.qso_quantum_create(
            uri=uri,
            payload={"object_kind": "quantum_lisp_program", "backend": "quantum_lisp", "source": source, "verification_hash": "0" * 64},
        )
        tools.qso_quantum_lisp_analyze(uri)
        analyze_uris.append(uri)

    analyze_result = _bench("persisted_analyze", iterations, analyze_once)

    def replay_once(idx: int) -> None:
        tools.qso_quantum_lisp_replay(analyze_uris[idx])

    replay_result = _bench("replay_trace", iterations, replay_once)

    def end_to_end_once(idx: int) -> None:
        compiled_cache["last"] = tools.qso_quantum_lisp_compile(source)
        uri = f"qso://quantum.state/qlisp_bench_e2e_{idx}"
        tools.qso_quantum_create(
            uri=uri,
            payload={"object_kind": "quantum_lisp_program", "backend": "quantum_lisp", "source": source, "verification_hash": "0" * 64},
        )
        tools.qso_quantum_lisp_analyze(uri)
        tools.qso_quantum_lisp_replay(uri)

    e2e_result = _bench("compile_analyze_replay", iterations, end_to_end_once)
    sample_ir = compiled_cache.get("last") or tools.qso_quantum_lisp_compile(source)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "engine": "qso.quantum_lisp",
        "iterations": iterations,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "source_hash": sample_ir["source_hash"],
        "ir_hash": sample_ir["ir_hash"],
        "backend_targets": sample_ir["backend_targets"],
        "results": [asdict(row) for row in (compile_result, analyze_result, replay_result, e2e_result)],
    }


def _markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Quantum LISP Benchmark Report",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Engine: `{payload['engine']}`",
        f"- Iterations: `{payload['iterations']}`",
        f"- Python: `{payload['python']}`",
        f"- Platform: `{payload['platform']}`",
        f"- Source hash: `{payload['source_hash']}`",
        f"- IR hash: `{payload['ir_hash']}`",
        f"- Backend targets: `{', '.join(payload['backend_targets'])}`",
        "",
        "| Benchmark | Iterations | Total ms | Mean ms | P50 ms | P95 ms | Min ms | Max ms | Ops/s |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["results"]:
        lines.append(
            f"| `{row['name']}` | {row['iterations']} | {row['total_ms']} | {row['mean_ms']} | "
            f"{row['p50_ms']} | {row['p95_ms']} | {row['min_ms']} | {row['max_ms']} | {row['throughput_ops_s']} |"
        )
    lines.append("")
    lines.append("Benchmarks use the built-in Quantum LISP demo source and the local deterministic backend fallbacks when native quantum libraries are unavailable.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark the QSO Quantum LISP reasoning engine")
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--json-out", default="reports/quantum_lisp_benchmark_latest.json")
    parser.add_argument("--md-out", default="reports/quantum_lisp_benchmark_latest.md")
    parser.add_argument("--source", default="", help="optional Quantum LISP source file")
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args(argv)

    source = Path(args.source).read_text(encoding="utf-8") if args.source else DEMO_SOURCE
    payload = run_benchmarks(iterations=args.iterations, source=source)

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_out.write_text(_markdown_report(payload), encoding="utf-8")

    if args.print_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_markdown_report(payload))


if __name__ == "__main__":
    main()
