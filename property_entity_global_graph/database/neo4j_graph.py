"""Graph storage with Neo4j optional and NetworkX fallback."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import networkx as nx


@dataclass
class GraphConfig:
    use_neo4j: bool = False
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"


class Neo4jGraph:
    def __init__(self, config: GraphConfig):
        self.config = config
        self.graph = nx.MultiDiGraph()
        self.driver = None
        if config.use_neo4j:
            try:
                from neo4j import GraphDatabase
            except Exception:
                self.driver = None
            else:
                try:
                    self.driver = GraphDatabase.driver(config.uri, auth=(config.user, config.password))
                except Exception:
                    self.driver = None

    def upsert_node(self, node_id: str, node_type: str, **attrs: Any) -> None:
        attrs = dict(attrs)
        attrs["type"] = node_type
        self.graph.add_node(node_id, **attrs)
        if self.driver:
            q = "MERGE (n:Entity {id:$id}) SET n += $props"
            with self.driver.session() as s:
                s.run(q, id=node_id, props=attrs)

    def add_edge(self, source: str, rel_type: str, target: str, **attrs: Any) -> None:
        self.graph.add_edge(source, target, type=rel_type, **attrs)
        if self.driver:
            q = (
                "MATCH (a:Entity {id:$source}), (b:Entity {id:$target}) "
                "MERGE (a)-[r:RELATED {type:$rel_type}]->(b) "
                "SET r += $props"
            )
            with self.driver.session() as s:
                s.run(q, source=source, target=target, rel_type=rel_type, props=attrs)

    def export_json(self, path: Path) -> Path:
        nodes = [{"id": n, **d} for n, d in self.graph.nodes(data=True)]
        edges = [{"source": u, "target": v, **d} for u, v, d in self.graph.edges(data=True)]
        payload = {"nodes": nodes, "edges": edges}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def neighbors(self, node_id: str) -> list[str]:
        if node_id not in self.graph:
            return []
        return sorted(self.graph.neighbors(node_id))

    def simple_paths(self, source: str, target: str, cutoff: int = 5) -> list[list[str]]:
        if source not in self.graph or target not in self.graph:
            return []
        ug = self.graph.to_undirected()
        return [list(p) for p in nx.all_simple_paths(ug, source=source, target=target, cutoff=cutoff)]
