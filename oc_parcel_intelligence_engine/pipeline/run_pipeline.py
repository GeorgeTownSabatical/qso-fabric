"""Main APN pipeline runner."""

from __future__ import annotations

import argparse
from pathlib import Path

from agents.assessor_agent import AssessorAgent
from agents.gis_agent import GISAgent
from agents.ownership_graph_agent import OwnershipGraph
from agents.recorder_agent import RecorderAgent
from core.apn_parser import normalize_apn
from storage.graph_store import save_graph_json, save_graphml
from storage.json_store import save_json


BASE_DIR = Path(__file__).resolve().parents[1]


def run_pipeline(apn: str) -> dict:
    parsed = normalize_apn(apn)
    formatted_apn = parsed["formatted"]

    assessor = AssessorAgent()
    recorder = RecorderAgent()
    gis = GISAgent()

    parcel_data = assessor.lookup(formatted_apn)
    docs = recorder.fetch_documents(formatted_apn)
    geo = gis.get_geometry(formatted_apn)

    graph = OwnershipGraph()
    graph.add_parcel(formatted_apn)

    for doc in docs:
        doc_id = doc["document_number"]
        graph.add_document(doc_id, doc.get("type", ""), doc.get("date", ""))
        graph.add_transfer(doc.get("grantor", "UNKNOWN"), doc.get("grantee", "UNKNOWN"), formatted_apn, doc_id)

    for neighbor in geo.get("neighbors", []):
        graph.add_adjacency(formatted_apn, neighbor)

    parcel_path = BASE_DIR / "data" / "parcels" / f"{formatted_apn}.json"
    docs_path = BASE_DIR / "data" / "documents" / f"{formatted_apn}_docs.json"
    graph_json_path = BASE_DIR / "data" / "graphs" / f"{formatted_apn}_graph.json"
    graphml_path = BASE_DIR / "data" / "graphs" / f"{formatted_apn}_graph.graphml"

    save_json(parcel_path, {"parsed_apn": parsed, "parcel": parcel_data, "geometry": geo})
    save_json(docs_path, docs)
    save_graph_json(graph, graph_json_path)
    save_graphml(graph.graph, graphml_path)

    return {
        "apn": formatted_apn,
        "parcel": parcel_data,
        "documents": docs,
        "geometry": geo,
        "graph_nodes": graph.graph.number_of_nodes(),
        "graph_edges": graph.graph.number_of_edges(),
        "artifacts": {
            "parcel": str(parcel_path),
            "documents": str(docs_path),
            "graph_json": str(graph_json_path),
            "graphml": str(graphml_path),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run parcel intelligence pipeline for one APN")
    parser.add_argument("apn", help="APN such as 405-112-17")
    args = parser.parse_args()

    result = run_pipeline(args.apn)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
