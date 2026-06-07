"""Main reasoning pipeline for graph AI layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.anomaly_agent import AnomalyAgent
from agents.beneficial_owner_agent import BeneficialOwnerAgent
from agents.cluster_agent import ClusterAgent
from agents.influence_agent import InfluenceAgent
from algorithms.link_prediction import predict_links
from core.feature_extractor import extract_features
from core.graph_embeddings import generate_embeddings
from core.graph_loader import load_graph_from_json
from visualization.cluster_viewer import export_clusters


def run_reasoning(graph_json: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    graph = load_graph_from_json(graph_json)

    features = extract_features(graph)
    embeddings = generate_embeddings(graph, dimensions=32)

    clusters = ClusterAgent().run(graph)
    anomalies = AnomalyAgent().run(graph)
    beneficial = BeneficialOwnerAgent().run(graph)
    influence = InfluenceAgent().run(graph, top_k=25)
    links = predict_links(graph, top_k=30)

    (output_dir / "features.json").write_text(json.dumps(features, indent=2), encoding="utf-8")
    (output_dir / "embeddings.json").write_text(json.dumps(embeddings, indent=2), encoding="utf-8")
    (output_dir / "clusters.json").write_text(json.dumps(clusters, indent=2), encoding="utf-8")
    (output_dir / "anomalies.json").write_text(json.dumps(anomalies, indent=2), encoding="utf-8")
    (output_dir / "beneficial_owner_inference.json").write_text(json.dumps(beneficial, indent=2), encoding="utf-8")
    (output_dir / "influence_hubs.json").write_text(json.dumps(influence, indent=2), encoding="utf-8")
    (output_dir / "link_predictions.json").write_text(json.dumps(links, indent=2), encoding="utf-8")
    export_clusters(clusters, output_dir / "clusters.csv")

    summary = {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "feature_nodes": len(features),
        "embedding_nodes": len(embeddings),
        "clusters": len(clusters),
        "rapid_transfer_parcels": len(anomalies.get("rapid_transfer_parcels", [])),
        "ownership_cycles": len(anomalies.get("ownership_cycles", [])),
        "beneficial_owner_candidates": len(beneficial),
        "influence_hubs": len(influence),
        "predicted_links": len(links),
    }
    (output_dir / "reasoning_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run graph reasoning pipeline")
    parser.add_argument("--graph-json", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "outputs")
    args = parser.parse_args()

    summary = run_reasoning(args.graph_json, args.output_dir)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
