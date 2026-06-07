"""Graph loader from Neo4j or local JSON artifact."""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx


def load_graph_from_json(path: Path) -> nx.MultiDiGraph:
    payload = json.loads(path.read_text(encoding="utf-8"))
    g = nx.MultiDiGraph()
    for node in payload.get("nodes", []):
        node_id = node.get("id")
        attrs = {k: v for k, v in node.items() if k != "id"}
        g.add_node(node_id, **attrs)
    for edge in payload.get("edges", []):
        src = edge.get("source")
        dst = edge.get("target")
        attrs = {k: v for k, v in edge.items() if k not in {"source", "target"}}
        g.add_edge(src, dst, **attrs)
    return g


def load_graph_from_neo4j(uri: str, user: str, password: str) -> nx.MultiDiGraph:
    from neo4j import GraphDatabase

    g = nx.MultiDiGraph()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        for record in session.run("MATCH (n) RETURN n.id AS id, labels(n) AS labels, properties(n) AS props"):
            node_id = record["id"]
            props = dict(record["props"] or {})
            labels = list(record["labels"] or [])
            if labels:
                props.setdefault("type", labels[0])
            g.add_node(node_id, **props)

        for record in session.run("MATCH (a)-[r]->(b) RETURN a.id AS source, b.id AS target, type(r) AS rel, properties(r) AS props"):
            attrs = dict(record["props"] or {})
            attrs.setdefault("type", record["rel"])
            g.add_edge(record["source"], record["target"], **attrs)
    driver.close()
    return g
