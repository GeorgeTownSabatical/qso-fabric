"""Feature extraction for graph nodes."""

from __future__ import annotations

from collections import Counter


def extract_features(graph) -> dict[str, dict]:
    degree = dict(graph.degree())
    incoming = dict(graph.in_degree())
    outgoing = dict(graph.out_degree())

    address_degree = Counter()
    for u, v, d in graph.edges(data=True):
        if d.get("type") == "REGISTERED_AT":
            address_degree[v] += 1

    features: dict[str, dict] = {}
    for node, attrs in graph.nodes(data=True):
        neighbors = set(graph.neighbors(node))
        ownership_count = sum(1 for _, _, d in graph.out_edges(node, data=True) if d.get("type") in {"OWNS", "OWNED_BY"})
        transfer_frequency = sum(1 for _, _, d in graph.out_edges(node, data=True) if d.get("type") == "TRANSFERRED")
        company_links = sum(1 for nbr in neighbors if graph.nodes[nbr].get("type") in {"Company", "LLC", "Corporation"})
        shared_addresses = sum(address_degree.get(nbr, 0) for nbr in neighbors if graph.nodes[nbr].get("type") == "Address")
        features[node] = {
            "node_type": attrs.get("type", "Unknown"),
            "degree": degree.get(node, 0),
            "in_degree": incoming.get(node, 0),
            "out_degree": outgoing.get(node, 0),
            "connections": len(neighbors),
            "ownership_count": ownership_count,
            "transfer_frequency": transfer_frequency,
            "company_links": company_links,
            "shared_addresses": shared_addresses,
        }
    return features
