#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHAMBER_SPECS: tuple[dict[str, Any], ...] = (
    {"id": 1, "arc": "Arc I", "title": "Deterministic Core Formalization", "files": ["solis/physics/fixed_math.py", "solis/shared/canonical_json.py"], "tests": ["test_fixed_math_determinism.py"]},
    {"id": 2, "arc": "Arc I", "title": "Global Invariant Definition", "files": ["solis/physics/invariants.py"], "tests": ["test_physics_invariants.py"]},
    {"id": 3, "arc": "Arc I", "title": "Risk & Collapse Engine", "files": ["solis/physics/collapse_engine.py", "solis/projectors/instability_engine.py"], "tests": ["test_physics_engines.py", "test_instability_thresholds.py"]},
    {"id": 4, "arc": "Arc I", "title": "Transsheaf Modeling Layer", "files": ["solis/physics/sheaf_model.py", "solis/physics/stability_solver.py"], "tests": ["test_contagion_stability_solver.py"]},
    {"id": 5, "arc": "Arc I", "title": "Entanglement Graph Hardening", "files": ["solis/entanglement/stellar_relationships.py", "solis/services/solis_constellation_service.py"], "tests": ["test_constellation_propagation.py"]},
    {"id": 6, "arc": "Arc I", "title": "Merkle Integrity Spine", "files": ["solis/merkle/merkle_tree.py", "solis/merkle/merkle_anchor.py", "solis/merkle/proof_verifier.py"], "tests": ["test_replay_determinism.py"]},
    {"id": 7, "arc": "Arc II", "title": "Iris Biometric Abstraction", "files": ["solis/identity/iris_hash.py"], "tests": ["test_identity_trust_layer.py"]},
    {"id": 8, "arc": "Arc II", "title": "Post-Quantum Key Infrastructure", "files": ["solis/identity/pq_keys.py"], "tests": ["test_identity_trust_layer.py"]},
    {"id": 9, "arc": "Arc II", "title": "Deterministic Recovery Model", "files": ["solis/identity/recovery_model.py"], "tests": ["test_identity_trust_layer.py"]},
    {"id": 10, "arc": "Arc II", "title": "ZK Risk Proof Layer", "files": ["solis/identity/zk/proof_adapter.py", "solis/identity/zk/verifier.py", "solis/zk/command_adapter.py"], "tests": ["test_identity_trust_layer.py", "test_zk_command_integration.py"]},
    {"id": 11, "arc": "Arc II", "title": "Public Anchor Strategy", "files": ["solis/anchor/eth_anchor.py", "solis/anchor/spherechain_anchor.py", "solis/anchor/anchor_contract.sol"], "tests": ["test_anchor_adapters.py"]},
    {"id": 12, "arc": "Arc II", "title": "Full Replay Auditor", "files": ["solis/agent/sandbox/replay_engine.py", "solis/integration/gates.py"], "tests": ["test_replay_determinism.py", "test_multinode_replay_matrix.py"]},
    {"id": 13, "arc": "Arc III", "title": "DSL Grammar Design", "files": ["solis/agent/dsl/grammar.lark", "solis/agent/dsl/parser.py"], "tests": ["test_agent_dsl_runtime.py"]},
    {"id": 14, "arc": "Arc III", "title": "DSL Compiler -> Execution DAG", "files": ["solis/agent/dsl/compiler.py", "solis/agent/runtime/execution_graph.py"], "tests": ["test_agent_dsl_runtime.py"]},
    {"id": 15, "arc": "Arc III", "title": "Policy Guard Engine", "files": ["solis/agent/runtime/policy_guard.py"], "tests": ["test_policy_guard_pre_execution.py", "test_runtime_admission_gates.py"]},
    {"id": 16, "arc": "Arc III", "title": "Agent Instance Runtime", "files": ["solis/agent/runtime/instance_state.py", "solis/agent/runtime/capital_router.py"], "tests": ["test_agent_dsl_runtime.py"]},
    {"id": 17, "arc": "Arc III", "title": "Agent Marketplace Layer", "files": ["solis/agent/marketplace/template_registry.py", "solis/agent/marketplace/versioning.py", "solis/agent/marketplace/revenue_model.py"], "tests": ["test_agent_dsl_runtime.py"]},
    {"id": 18, "arc": "Arc III", "title": "Replay + Backtest Engine", "files": ["solis/agent/sandbox/replay_engine.py", "solis/simulation/stress_report.py"], "tests": ["test_replay_determinism.py"]},
    {"id": 19, "arc": "Arc IV", "title": "Portfolio Agent Factory", "files": ["solis/services/solis_star_service.py", "solis/agent/runtime/instance_state.py"], "tests": ["test_agent_dsl_runtime.py"]},
    {"id": 20, "arc": "Arc IV", "title": "Capital Router", "files": ["solis/agent/runtime/capital_router.py", "solis/services/solis_constellation_service.py"], "tests": ["test_constellation_propagation.py"]},
    {"id": 21, "arc": "Arc IV", "title": "Systemic Risk Pricing", "files": ["solis/physics/entropy_engine.py", "solis/physics/stability_solver.py"], "tests": ["test_contagion_stability_solver.py"]},
    {"id": 22, "arc": "Arc IV", "title": "Auto-Rebalance Engine", "files": ["solis/services/solis_constellation_service.py", "solis/agent/runtime/risk_adapter.py"], "tests": ["test_constellation_propagation.py"]},
    {"id": 23, "arc": "Arc IV", "title": "Loan & Credit Primitive", "files": ["solis/agent/runtime/policy_guard.py"], "tests": []},
    {"id": 24, "arc": "Arc IV", "title": "Cross-Agent Influence Monitor", "files": ["solis/services/solis_constellation_service.py", "solis/physics/contagion_engine.py"], "tests": ["test_contagion_stability_solver.py"]},
    {"id": 25, "arc": "Arc V", "title": "Constellation Visualizer", "files": ["solis/renderer/web/stellar_scene.js", "solis/renderer/stellar_socket.py"], "tests": []},
    {"id": 26, "arc": "Arc V", "title": "Agent Inspector API", "files": ["solis/mcp_tools/solis_tools.py"], "tests": []},
    {"id": 27, "arc": "Arc V", "title": "Stability Dashboard", "files": ["solis/services/solis_meta_signal_service.py", "solis/reports/scripts/generate_report.py"], "tests": ["test_gate_decision_events.py"]},
    {"id": 28, "arc": "Arc V", "title": "Whale Mode Advanced Controls", "files": ["solis/mcp_tools/solis_tools.py", "solis/agent/dsl/compiler.py"], "tests": []},
    {"id": 29, "arc": "Arc V", "title": "Regulatory Audit Interface", "files": ["solis/integration/gates.py", "solis/services/gate_audit.py"], "tests": ["test_integration_gates.py"]},
    {"id": 30, "arc": "Arc V", "title": "AI Meta-Learning Console", "files": ["solis/gdml/solis_optimizer.py", "solis/gdml/solis_reward_adapter.py"], "tests": []},
    {"id": 31, "arc": "Arc VI", "title": "Civilian Mode UX", "files": ["solis/renderer/web/index.html", "solis/renderer/web/solis_client.js"], "tests": []},
    {"id": 32, "arc": "Arc VI", "title": "Language-Agnostic Interaction", "files": ["solis/renderer/web/index.html"], "tests": []},
    {"id": 33, "arc": "Arc VI", "title": "Payment Rail Integration", "files": ["solis/services/solis_star_service.py"], "tests": []},
    {"id": 34, "arc": "Arc VI", "title": "Energy & Productivity Linkage", "files": ["solis/gdml/solis_reward_adapter.py"], "tests": []},
    {"id": 35, "arc": "Arc VI", "title": "Governance Constellation", "files": ["solis/schemas/governance.schema.json", "solis/services/solis_constellation_service.py"], "tests": []},
    {"id": 36, "arc": "Arc VI", "title": "Planetary Stability Index", "files": ["solis/constellation/planetary_index.py", "solis/constellation/contagion_graph.py", "solis/constellation/resonance_engine.py"], "tests": []},
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate versioned Solis progress report bundle")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--version", default="", help="Version id (default: derived from timestamp)")
    parser.add_argument("--timestamp", default="", help="UTC timestamp in ISO-8601 (default: now)")
    parser.add_argument("--validate-only", default="0", help="1/true to write to temp and skip latest/index updates")
    return parser.parse_args()


def as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def pct(part: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return round((part / total) * 100.0, 1)


def parse_timestamp(raw: str) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    value = raw.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def render_bar_chart_svg(
    *,
    title: str,
    subtitle: str,
    items: list[tuple[str, float, str]],
    width: int = 1200,
    row_h: int = 56,
) -> str:
    margin_l = 340
    margin_r = 180
    margin_t = 110
    margin_b = 70
    plot_w = width - margin_l - margin_r
    height = margin_t + margin_b + row_h * len(items)

    bg = "#f8fafc"
    fg = "#0f172a"
    sub = "#334155"
    grid = "#cbd5e1"
    bar = "#0ea5e9"
    bar2 = "#22c55e"

    out: list[str] = []
    out.append(f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>")
    out.append(f"<rect width='{width}' height='{height}' fill='{bg}'/>")
    out.append(f"<text x='40' y='52' font-family='Menlo, monospace' font-size='34' fill='{fg}'>{esc(title)}</text>")
    out.append(f"<text x='40' y='82' font-family='Menlo, monospace' font-size='18' fill='{sub}'>{esc(subtitle)}</text>")

    for tick in [0, 25, 50, 75, 100]:
        x = margin_l + int(plot_w * (tick / 100.0))
        out.append(f"<line x1='{x}' y1='{margin_t-20}' x2='{x}' y2='{height-margin_b+8}' stroke='{grid}' stroke-width='1'/>")
        out.append(f"<text x='{x-12}' y='{height-margin_b+36}' font-family='Menlo, monospace' font-size='14' fill='{sub}'>{tick}%</text>")

    for idx, (label, value, extra) in enumerate(items):
        y = margin_t + idx * row_h
        width_val = int(plot_w * max(0.0, min(100.0, value)) / 100.0)
        color = bar if idx % 2 == 0 else bar2
        out.append(f"<text x='40' y='{y+26}' font-family='Menlo, monospace' font-size='17' fill='{fg}'>{esc(label)}</text>")
        out.append(f"<rect x='{margin_l}' y='{y+8}' width='{plot_w}' height='24' fill='#e2e8f0' rx='4' ry='4'/>")
        out.append(f"<rect x='{margin_l}' y='{y+8}' width='{width_val}' height='24' fill='{color}' rx='4' ry='4'/>")
        out.append(f"<text x='{margin_l + plot_w + 18}' y='{y+26}' font-family='Menlo, monospace' font-size='16' fill='{fg}'>{value:.1f}%</text>")
        out.append(f"<text x='{margin_l + plot_w + 88}' y='{y+26}' font-family='Menlo, monospace' font-size='14' fill='{sub}'>{esc(extra)}</text>")

    out.append("</svg>")
    return "".join(out)


def write_svg_png(target_dir: Path, name: str, svg: str, *, validate_only: bool, warnings: list[str]) -> None:
    svg_path = target_dir / f"{name}.svg"
    svg_path.write_text(svg, encoding="utf-8")

    if validate_only:
        return
    if shutil.which("sips") is None:
        warnings.append(f"sips unavailable; skipped PNG for {name}")
        return
    png_path = target_dir / f"{name}.png"
    subprocess.run(
        ["sips", "-s", "format", "png", str(svg_path), "--out", str(png_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def collect_completion(root: Path) -> tuple[list[tuple[str, float, str]], dict[str, dict[str, Any]], dict[str, Any]]:
    groups = OrderedDict(
        {
            "Core runtime": [
                "solis/config.py",
                "solis/schemas/star.schema.json",
                "solis/schemas/validator.schema.json",
                "solis/schemas/contract.schema.json",
                "solis/schemas/token.schema.json",
                "solis/schemas/governance.schema.json",
                "solis/schemas/constellation.schema.json",
                "solis/schemas/stellar_event.schema.json",
                "solis/projectors/stellar_projector_v1.py",
                "solis/projectors/instability_engine.py",
                "solis/entanglement/stellar_relationships.py",
                "solis/services/solis_star_service.py",
                "solis/services/solis_constellation_service.py",
                "solis/services/solis_meta_signal_service.py",
                "solis/mcp_tools/solis_tools.py",
                "solis/mcp_tools/solis_stream.py",
                "solis/README.md",
            ],
            "Merkle hardening": [
                "solis/merkle/merkle_tree.py",
                "solis/merkle/merkle_anchor.py",
                "solis/merkle/proof_verifier.py",
            ],
            "GDML binding": [
                "solis/gdml/solis_reward_adapter.py",
                "solis/gdml/solis_policy_sync.py",
                "solis/gdml/solis_optimizer.py",
            ],
            "Deployment assets": [
                "infra/docker/Dockerfile.solis",
                "infra/docker/entrypoint.sh",
                "infra/docker/docker-compose.solis.yml",
                "infra/k8s/solis-configmap.yaml",
                "infra/k8s/solis-secrets.yaml",
                "infra/k8s/solis-deployment.yaml",
                "infra/k8s/solis-service.yaml",
                "infra/k8s/solis-hpa.yaml",
                "Makefile",
            ],
            "Phase 8-14 extensions": [
                "solis/anchor/eth_anchor.py",
                "solis/anchor/spherechain_anchor.py",
                "solis/anchor/anchor_contract.sol",
                "solis/anchor/anchor_cli.py",
                "solis/zk/collapse_circuit.circom",
                "solis/zk/generate_proof.py",
                "solis/zk/verify_proof.py",
                "solis/simulation/shock_generator.py",
                "solis/simulation/cascade_simulator.py",
                "solis/simulation/monte_deterministic.py",
                "solis/simulation/stress_report.py",
                "solis/renderer/server.py",
                "solis/renderer/stellar_socket.py",
                "solis/renderer/web/index.html",
                "solis/renderer/web/stellar_scene.js",
                "solis/renderer/web/solis_client.js",
                "solis/constellation/planetary_index.py",
                "solis/constellation/contagion_graph.py",
                "solis/constellation/resonance_engine.py",
                "solis/hardening/metrics_exporter.py",
                "solis/hardening/tracing.py",
                "solis/hardening/rate_limit.py",
                "solis/hardening/policy_gate.py",
            ],
            "CI workflow": [".github/workflows/solis-ci.yml"],
        }
    )

    rows: list[tuple[str, float, str]] = []
    by_group: dict[str, dict[str, Any]] = {}
    for group, files in groups.items():
        present = sum(1 for path in files if (root / path).exists())
        total = len(files)
        percent = pct(present, total)
        rows.append((group, percent, f"{present}/{total}"))
        by_group[group] = {"present": present, "total": total, "percent": percent}

    overall_present = sum(v["present"] for v in by_group.values())
    overall_total = sum(v["total"] for v in by_group.values())
    overall = {"present": overall_present, "total": overall_total, "percent": pct(overall_present, overall_total)}
    return rows, by_group, overall


def collect_tests(root: Path) -> tuple[list[tuple[str, float, str]], dict[str, int], int]:
    area_map = {
        "test_fixed_math_determinism.py": "Arc I Physics",
        "test_physics_engines.py": "Arc I Physics",
        "test_physics_invariants.py": "Arc I Physics",
        "test_contagion_stability_solver.py": "Arc I Physics",
        "test_instability_thresholds.py": "Arc I Physics",
        "test_identity_trust_layer.py": "Arc II Identity/Trust",
        "test_anchor_adapters.py": "Arc II Identity/Trust",
        "test_zk_command_integration.py": "Arc II Identity/Trust",
        "test_agent_dsl_runtime.py": "Arc III Dev Layer",
        "test_integration_gates.py": "Arc III Dev Layer",
        "test_policy_guard_pre_execution.py": "Runtime Admission",
        "test_runtime_admission_gates.py": "Runtime Admission",
        "test_gate_decision_events.py": "Runtime Admission",
        "test_stellar_projection.py": "Service/Replay",
        "test_replay_determinism.py": "Service/Replay",
        "test_constellation_propagation.py": "Service/Replay",
        "test_multinode_replay_matrix.py": "Service/Replay",
    }

    counts: Counter[str] = Counter()
    tests_dir = root / "solis/tests"
    for path in sorted(tests_dir.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
        if path.name == "test_multinode_replay_matrix.py":
            count = 6
        counts[area_map.get(path.name, "Other")] += count

    total = sum(counts.values())
    rows = [(name, pct(value, total), f"{value} tests") for name, value in sorted(counts.items())]
    return rows, dict(counts), total


def collect_gate_sample() -> tuple[list[tuple[str, float, str]], list[tuple[str, float, str]], list[tuple[str, float, str]], dict[str, dict[str, int]], int]:
    from solis.config import SolisConfig
    from solis.services.solis_constellation_service import SolisConstellationService
    from solis.services.solis_meta_signal_service import SolisMetaSignalService
    from solis.services.solis_star_service import SolisStarService

    cfg = SolisConfig(anchor_interval=2, runtime_gate_enabled=True)
    stars = SolisStarService(config=cfg)
    constell = SolisConstellationService(star_service=stars, config=cfg)
    signals = SolisMetaSignalService(star_service=stars, config=cfg)

    stars.create_star(star_id="rep_a", chain_id="spherechain")
    stars.create_star(star_id="rep_b", chain_id="spherechain")
    stars.patch_star(star_uri_or_id="rep_a", delta={"mass": 0.2, "luminosity": 0.1, "entropy_index": 0.01, "magnetic_field": -0.005})
    constell.create_constellation(domain="rep", star_uris=["rep_a", "rep_b"])
    constell.recompute_constellation("rep")
    signals.emit_signals("rep_a")

    scope_counter: Counter[str] = Counter()
    stage_counter: Counter[str] = Counter()
    gate_counter: Counter[str] = Counter()

    uris = [u for u in stars.qso.tools.runtime.registry.list_uris() if u.startswith("qso://solis.gate.")]
    for uri in uris:
        payload = stars.qso.read(uri).get("state_layer", {})
        # Exclude rollup/health objects from event-distribution charts.
        if not {"scope", "stage", "gate"}.issubset(payload.keys()):
            continue
        scope_counter[str(payload.get("scope", "unknown"))] += 1
        stage_counter[str(payload.get("stage", "unknown"))] += 1
        gate_counter[str(payload.get("gate", "unknown"))] += 1

    total = sum(scope_counter.values())
    scope_rows = [(k, pct(v, total), f"{v} events") for k, v in sorted(scope_counter.items())]
    stage_rows = [(k, pct(v, total), f"{v} events") for k, v in sorted(stage_counter.items())]
    gate_rows = [(k, pct(v, total), f"{v} events") for k, v in sorted(gate_counter.items())]

    raw = {
        "by_scope": dict(scope_counter),
        "by_stage": dict(stage_counter),
        "by_gate": dict(gate_counter),
    }
    return scope_rows, stage_rows, gate_rows, raw, total


def collect_footprint(root: Path) -> tuple[list[tuple[str, float, str]], dict[str, dict[str, int]], int]:
    sections: OrderedDict[str, dict[str, int]] = OrderedDict()
    for sub in [
        "services",
        "tests",
        "physics",
        "agent",
        "identity",
        "projectors",
        "schemas",
        "merkle",
        "mcp_tools",
        "gdml",
        "simulation",
        "renderer",
        "constellation",
        "hardening",
        "integration",
        "shared",
        "anchor",
        "zk",
        "entanglement",
    ]:
        path = root / "solis" / sub
        files = [f for f in path.rglob("*") if f.is_file() and "__pycache__" not in f.parts] if path.exists() else []
        lines = 0
        for file_path in files:
            try:
                with file_path.open("r", encoding="utf-8") as handle:
                    lines += sum(1 for _ in handle)
            except Exception:
                continue
        sections[sub] = {"files": len(files), "lines": lines}

    total_loc = sum(v["lines"] for v in sections.values())
    top = sorted(sections.items(), key=lambda kv: kv[1]["lines"], reverse=True)
    top6 = top[:6]
    other_loc = sum(v["lines"] for _, v in top[6:])
    rows = [(name, pct(data["lines"], total_loc), f"{data['lines']} LOC") for name, data in top6]
    rows.append(("other", pct(other_loc, total_loc), f"{other_loc} LOC"))
    return rows, dict(sections), total_loc


def collect_chambers(root: Path) -> tuple[list[tuple[str, float, str]], dict[str, Any], dict[str, int]]:
    tests_dir = root / "solis/tests"
    test_set = {p.name for p in tests_dir.glob("test_*.py")} if tests_dir.exists() else set()

    by_arc_status: dict[str, Counter[str]] = {}
    chambers: list[dict[str, Any]] = []

    for spec in CHAMBER_SPECS:
        files = [str(p) for p in spec["files"]]
        tests = [str(t) for t in spec["tests"]]
        found_files = [p for p in files if (root / p).exists()]
        found_tests = [t for t in tests if t in test_set]
        required_count = len(files) + len(tests)
        satisfied_count = len(found_files) + len(found_tests)

        if required_count == 0:
            status = "planned"
        elif satisfied_count == required_count:
            status = "complete"
        elif satisfied_count > 0:
            status = "partial"
        else:
            status = "planned"

        coverage = pct(satisfied_count, required_count if required_count else 1)
        chamber = {
            "id": spec["id"],
            "arc": spec["arc"],
            "title": spec["title"],
            "status": status,
            "coverage_percent": coverage,
            "evidence": {
                "required_files": files,
                "required_tests": tests,
                "found_files": found_files,
                "found_tests": found_tests,
            },
        }
        chambers.append(chamber)
        by_arc_status.setdefault(spec["arc"], Counter())[status] += 1

    totals = Counter(row["status"] for row in chambers)
    rows: list[tuple[str, float, str]] = []
    for status in ("complete", "partial", "planned"):
        count = totals.get(status, 0)
        rows.append((status, pct(count, len(chambers)), f"{count} chambers"))

    by_arc = {
        arc: {
            "complete": counts.get("complete", 0),
            "partial": counts.get("partial", 0),
            "planned": counts.get("planned", 0),
            "total": sum(counts.values()),
        }
        for arc, counts in sorted(by_arc_status.items())
    }
    summary = {
        "total": len(chambers),
        "complete": totals.get("complete", 0),
        "partial": totals.get("partial", 0),
        "planned": totals.get("planned", 0),
    }
    raw = {"chambers": chambers, "by_arc": by_arc}
    return rows, raw, summary


def write_tasks_list(path: Path) -> None:
    content = """# Solis Next Task List

## P0
1. Finish fixed-point migration at the projector/service boundary (eliminate residual float math in stellar projection fields).
2. Add live integration tests for Ethereum/SphereChain anchor adapters against local dev chains.
3. Make circom/snarkjs artifacts first-class in CI when toolchain is present (command path smoke test + fallback path test).
4. Add nightly long-run deterministic replay job (1000-event, 3-node matrix with state/merkle/anchor hash assertions).

## P1
5. Add policy-manifest-driven contagion/cascade deny rules with explicit QSO gate decision evidence.
6. Expand observability hardening tests (Prometheus scrape payload and OTEL exporter wiring).
7. Extend gate health rollups with windowed SLOs (24h/7d pass-rate envelopes and drift alerts).
8. Formalize 36-chamber evidence map: each chamber linked to code artifacts, tests, and acceptance checks.

## P2
9. Developer marketplace hardening: signed strategy manifests, provenance labels, and deterministic fee settlement checks.
10. Civilian/Sovereign/Architect mode permission graph wiring with invariant-backed transition tests.
11. Sovereign identity rollout hardening: device attestation verification path and recovery quorum lifecycle tests.
12. Publish a chamber-completion dashboard generated from report stats + gate history snapshots.
"""
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    validate_only = as_bool(args.validate_only)
    ts = parse_timestamp(args.timestamp)
    version = args.version.strip() or ts.strftime("v%Y%m%dT%H%M%SZ")

    if validate_only:
        out_dir = root / "solis/reports/.tmp-validation" / version
    else:
        out_dir = root / "solis/reports/versions" / version
    out_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []

    completion_rows, completion_raw, completion_overall = collect_completion(root)
    test_rows, test_raw, test_total = collect_tests(root)
    scope_rows, stage_rows, gate_rows, gate_raw, gate_total = collect_gate_sample()
    footprint_rows, footprint_raw, total_loc = collect_footprint(root)
    chamber_rows, chamber_raw, chamber_summary = collect_chambers(root)

    charts_dir = out_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    write_svg_png(
        charts_dir,
        "completion",
        render_bar_chart_svg(
            title="Solis Completion by Build Domain",
            subtitle=f"Overall: {completion_overall['present']}/{completion_overall['total']} ({completion_overall['percent']:.1f}%)",
            items=completion_rows,
        ),
        validate_only=validate_only,
        warnings=warnings,
    )
    write_svg_png(
        charts_dir,
        "tests",
        render_bar_chart_svg(
            title="Solis Test Distribution",
            subtitle=f"Total tests: {test_total}",
            items=test_rows,
        ),
        validate_only=validate_only,
        warnings=warnings,
    )
    write_svg_png(
        charts_dir,
        "gate_scope",
        render_bar_chart_svg(
            title="Runtime Gate Events by Scope",
            subtitle=f"Sampled events: {gate_total}",
            items=scope_rows,
        ),
        validate_only=validate_only,
        warnings=warnings,
    )
    write_svg_png(
        charts_dir,
        "gate_stage",
        render_bar_chart_svg(
            title="Runtime Gate Events by Stage",
            subtitle=f"Sampled events: {gate_total}",
            items=stage_rows,
        ),
        validate_only=validate_only,
        warnings=warnings,
    )
    write_svg_png(
        charts_dir,
        "gate_type",
        render_bar_chart_svg(
            title="Runtime Gate Events by Type",
            subtitle=f"Sampled events: {gate_total}",
            items=gate_rows,
        ),
        validate_only=validate_only,
        warnings=warnings,
    )
    write_svg_png(
        charts_dir,
        "footprint",
        render_bar_chart_svg(
            title="Solis Code Footprint",
            subtitle=f"Total LOC: {total_loc}",
            items=footprint_rows,
        ),
        validate_only=validate_only,
        warnings=warnings,
    )
    write_svg_png(
        charts_dir,
        "chambers",
        render_bar_chart_svg(
            title="36-Chamber Completion Status",
            subtitle=(
                f"Complete: {chamber_summary['complete']}/{chamber_summary['total']} | "
                f"Partial: {chamber_summary['partial']} | Planned: {chamber_summary['planned']}"
            ),
            items=chamber_rows,
        ),
        validate_only=validate_only,
        warnings=warnings,
    )

    stats = {
        "version": version,
        "generated_at": ts.isoformat(),
        "validate_only": validate_only,
        "warnings": warnings,
        "completion": {
            "overall": completion_overall,
            "by_group": completion_raw,
        },
        "tests": {
            "total": test_total,
            "by_area": test_raw,
        },
        "gate_event_sample": {
            "total": gate_total,
            **gate_raw,
        },
        "code_footprint": {
            "total_loc": total_loc,
            "by_section": footprint_raw,
        },
        "chambers": {
            "summary": chamber_summary,
            "detail": chamber_raw,
        },
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "chambers.json").write_text(json.dumps(chamber_raw, indent=2, sort_keys=True), encoding="utf-8")

    write_tasks_list(out_dir / "tasks_list.txt")

    overview = (
        f"# Solis Progress Report ({version})\n\n"
        f"Generated: {ts.isoformat()}\n\n"
        f"- Completion: {completion_overall['present']}/{completion_overall['total']} ({completion_overall['percent']:.1f}%)\n"
        f"- Tests: {test_total}\n"
        f"- Gate sample events: {gate_total}\n"
        f"- LOC: {total_loc}\n"
        f"- Chambers: {chamber_summary['complete']}/{chamber_summary['total']} complete, "
        f"{chamber_summary['partial']} partial, {chamber_summary['planned']} planned\n"
    )
    (out_dir / "overview.md").write_text(overview, encoding="utf-8")

    if not validate_only:
        reports_root = root / "solis/reports"
        reports_root.mkdir(parents=True, exist_ok=True)
        (reports_root / "LATEST").write_text(f"versions/{version}\n", encoding="utf-8")
        index = reports_root / "index.md"
        line = f"- [versions/{version}](versions/{version}/overview.md)"
        if index.exists():
            lines = index.read_text(encoding="utf-8").splitlines()
            if not lines:
                lines = ["# Solis Reports", "", line]
            else:
                if lines[0].strip() != "# Solis Reports":
                    lines = ["# Solis Reports", ""] + lines
                if line not in lines:
                    lines.append(line)
            index.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        else:
            index.write_text(f"# Solis Reports\n\n{line}\n", encoding="utf-8")

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
