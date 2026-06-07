"""Ownership graph builder using NetworkX."""

from __future__ import annotations

import networkx as nx


class OwnershipGraph:
    def __init__(self):
        self.graph = nx.MultiDiGraph()

    def add_parcel(self, apn: str):
        self.graph.add_node(apn, type="parcel")

    def add_owner(self, name: str):
        self.graph.add_node(name, type="entity")

    def add_document(self, document_number: str, doc_type: str, date: str):
        self.graph.add_node(document_number, type="document", doc_type=doc_type, date=date)

    def add_transfer(self, grantor: str, grantee: str, apn: str, document_number: str):
        self.add_owner(grantor)
        self.add_owner(grantee)
        self.add_parcel(apn)
        self.graph.add_edge(grantor, apn, type="OWNS")
        self.graph.add_edge(apn, grantee, type="TRANSFERRED_TO")
        self.graph.add_edge(document_number, apn, type="RECORDED_IN")

    def add_adjacency(self, apn: str, neighbor_apn: str):
        self.add_parcel(apn)
        self.add_parcel(neighbor_apn)
        self.graph.add_edge(apn, neighbor_apn, type="ADJACENT_TO")

    def to_dict(self) -> dict:
        nodes = [{"id": n, **attrs} for n, attrs in self.graph.nodes(data=True)]
        edges = [{"source": u, "target": v, **attrs} for u, v, attrs in self.graph.edges(data=True)]
        return {"nodes": nodes, "edges": edges}
