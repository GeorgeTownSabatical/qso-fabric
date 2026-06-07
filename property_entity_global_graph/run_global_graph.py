"""Build and analyze unified property/entity global graph."""

from __future__ import annotations

import json
import os
from pathlib import Path

from agents.entity_resolution_agent import EntityResolutionAgent
from agents.network_expansion_agent import expand_network
from agents.relationship_builder_agent import RelationshipBuilderAgent
from analysis.beneficial_owner_detector import detect as detect_beneficial
from analysis.control_inference_engine import infer_control
from analysis.layered_obfuscation_detector import detect as detect_obfuscation
from analysis.shell_company_chain_detector import detect as detect_shell
from analysis.surname_cluster_engine import analyze as analyze_surnames
from analysis.transfer_velocity_engine import detect as detect_velocity
from core.identity_resolution import EntitySnapshot
from database.event_store import EventStore
from database.neo4j_graph import GraphConfig, Neo4jGraph
from ingestion.corporate_registry_ingestor import ingest as ingest_corporate
from ingestion.court_record_ingestor import ingest as ingest_court
from ingestion.parcel_ingestor import ingest as ingest_parcels
from ingestion.recorder_ingestor import ingest as ingest_recorder
from ingestion.sec_filing_ingestor import ingest as ingest_sec
from visualization.cluster_heatmap import export_cluster_table
from visualization.graph_explorer import export_html
from visualization.timeline_viewer import build_parcel_timeline

BASE = Path(__file__).resolve().parent
OUT = BASE / "data" / "outputs"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    cfg = GraphConfig(
        use_neo4j=os.getenv("USE_NEO4J", "0") == "1",
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
    )
    graph_store = Neo4jGraph(cfg)
    event_store = EventStore(OUT / "event_log.jsonl")
    builder = RelationshipBuilderAgent(graph_store, event_store)

    parcel_rows = ingest_parcels()
    recorder_rows = ingest_recorder()
    corp_rows = ingest_corporate()
    sec_rows = ingest_sec()
    court_rows = ingest_court()

    builder.ingest_parcels(parcel_rows)
    builder.ingest_recorder_docs(recorder_rows)
    builder.ingest_corporate_registry(corp_rows)
    builder.ingest_sec_filings(sec_rows)
    builder.ingest_court_records(court_rows)

    graph_json_path = graph_store.export_json(OUT / "global_graph.json")

    beneficial = detect_beneficial(graph_store)
    shell = detect_shell(graph_store)
    surname_clusters = analyze_surnames(graph_store)
    velocity = detect_velocity(graph_store)
    control = infer_control(graph_store, threshold=0.5, max_depth=4)
    obfuscation = detect_obfuscation(graph_store)
    expansion = expand_network(graph_store, "405-112-17", depth=2)
    timeline = build_parcel_timeline(graph_store, "405-112-17")

    snapshots = [
        EntitySnapshot(name="Jacob T Messer", address="101 Harbor Street Orange CA", neighbors={"MESNER HOLDINGS LLC", "405-112-17"}, created_day=7000, transfer_days=[15, 30, 20]),
        EntitySnapshot(name="J T Messer", address="101 Harbor St Orange CA", neighbors={"MESNER HOLDINGS LLC", "405-112-18"}, created_day=7012, transfer_days=[18, 28, 22]),
        EntitySnapshot(name="Smith Trust", address="900 Other Ave Irvine CA", neighbors={"405-112-17"}, created_day=5000, transfer_days=[180, 240]),
    ]
    probabilistic_links = EntityResolutionAgent().probabilistic_links(snapshots, threshold=0.70)

    (OUT / "beneficial_owner_report.json").write_text(json.dumps(beneficial, indent=2), encoding="utf-8")
    (OUT / "shell_company_report.json").write_text(json.dumps(shell, indent=2), encoding="utf-8")
    (OUT / "surname_cluster_report.json").write_text(json.dumps(surname_clusters, indent=2), encoding="utf-8")
    (OUT / "transfer_velocity_report.json").write_text(json.dumps(velocity, indent=2), encoding="utf-8")
    (OUT / "control_inference_report.json").write_text(json.dumps(control, indent=2), encoding="utf-8")
    (OUT / "layered_obfuscation_report.json").write_text(json.dumps(obfuscation, indent=2), encoding="utf-8")
    (OUT / "network_expansion_report.json").write_text(json.dumps(expansion, indent=2), encoding="utf-8")
    (OUT / "parcel_timeline_405-112-17.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    (OUT / "identity_probability_report.json").write_text(json.dumps(probabilistic_links, indent=2), encoding="utf-8")

    export_cluster_table(
        [{"surname": row["surname"], "count": row["count"]} for row in surname_clusters],
        OUT / "surname_cluster_heatmap.csv",
    )
    export_html(graph_store, OUT / "graph_explorer.html")

    summary = {
        "graph_json": str(graph_json_path),
        "node_count": graph_store.graph.number_of_nodes(),
        "edge_count": graph_store.graph.number_of_edges(),
        "beneficial_owner_findings": len(beneficial),
        "shell_shared_address_clusters": len(shell.get("shared_address_clusters", [])),
        "surname_clusters": len(surname_clusters),
        "velocity_flags": len(velocity),
        "control_networks": len(control.get("controllers", [])),
        "obfuscation_entities_flagged": len([x for x in obfuscation if x.get("obfuscation_score", 0) >= 0.7]),
        "probabilistic_links": len(probabilistic_links),
    }
    (OUT / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
