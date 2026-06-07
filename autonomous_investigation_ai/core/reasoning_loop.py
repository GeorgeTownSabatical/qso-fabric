"""Single autonomous reasoning loop execution."""

from __future__ import annotations

import json
from pathlib import Path

from agents.data_acquisition_agent import DataAcquisitionAgent
from agents.graph_query_agent import GraphQueryAgent
from agents.hypothesis_generator_agent import HypothesisGeneratorAgent
from agents.verification_agent import VerificationAgent
from memory.evidence_store import EvidenceStore
from memory.hypothesis_store import HypothesisStore
from memory.knowledge_updates import KnowledgeUpdateStore


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def run_cycle(graph_json: Path, reasoning_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    reasoning_summary = _load_json(reasoning_dir / "reasoning_summary.json", {})
    anomalies = _load_json(reasoning_dir / "anomalies.json", {})
    clusters = _load_json(reasoning_dir / "clusters.json", [])
    influence = _load_json(reasoning_dir / "influence_hubs.json", [])

    graph_agent = GraphQueryAgent(graph_json)
    hypothesis_agent = HypothesisGeneratorAgent()
    acquisition_agent = DataAcquisitionAgent(graph_agent)
    verifier = VerificationAgent()

    hypothesis_store = HypothesisStore(output_dir / "hypothesis_store.json")
    evidence_store = EvidenceStore(output_dir / "evidence_store.json")
    knowledge_store = KnowledgeUpdateStore(output_dir / "knowledge_updates.json")

    hypotheses = hypothesis_agent.generate(reasoning_summary, anomalies, clusters, influence)

    verified = []
    for h in hypotheses:
        evidence = acquisition_agent.gather(h)
        result = verifier.verify(h, evidence)
        verified.append(result)
        evidence_store.append(result["hypothesis_id"], evidence)
        hypothesis_store.upsert(result)
        if result["status"] == "confirmed":
            knowledge_store.append(
                {
                    "hypothesis_id": result["hypothesis_id"],
                    "description": result["description"],
                    "confidence": result["confidence"],
                    "kind": result["type"],
                }
            )

    report = {
        "generated_hypotheses": len(hypotheses),
        "confirmed": len([r for r in verified if r["status"] == "confirmed"]),
        "rejected": len([r for r in verified if r["status"] == "rejected"]),
        "needs_more_data": len([r for r in verified if r["status"] == "needs more data"]),
        "active_hypotheses": len([r for r in verified if r["status"] == "open"]),
        "results": verified,
    }
    (output_dir / "autonomous_cycle_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
