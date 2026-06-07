"""Infer likely control relationships beyond legal ownership."""

from __future__ import annotations

from collections import defaultdict
import networkx as nx


EDGE_WEIGHTS = {
    "OWNS": 1.0,
    "OWNED_BY": 0.95,
    "DIRECTOR_OF": 0.7,
    "MANAGER_OF": 0.8,
    "REGISTERED_AT": 0.4,
    "TRANSFERRED": 0.5,
    "SIGNATORY": 0.6,
    "OFFICER_OF": 0.7,
    "SUBSIDIARY_OF": 0.65,
    "RELATED_TO": 0.3,
    "RECORDED_IN": 0.2,
    "INVOLVED_IN": 0.2,
}


def _path_weight(graph: nx.MultiDiGraph, path: list[str]) -> float:
    if len(path) < 2:
        return 0.0
    weight = 1.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_data = graph.get_edge_data(u, v, default={})
        if not edge_data:
            step = 0.2
        else:
            values = []
            for _, attrs in edge_data.items():
                rel = attrs.get("type", "RELATED_TO")
                values.append(EDGE_WEIGHTS.get(rel, 0.2))
            step = max(values) if values else 0.2
        weight *= step
    length_factor = 1.0 / max(len(path) - 1, 1)
    return weight * length_factor


def _controller_candidates(graph: nx.MultiDiGraph) -> list[str]:
    out = []
    for node, attrs in graph.nodes(data=True):
        if attrs.get("type") in {"Person", "Trust", "LLC", "Corporation", "Company"}:
            out.append(node)
    return out


def _asset_nodes(graph: nx.MultiDiGraph) -> list[str]:
    return [n for n, attrs in graph.nodes(data=True) if attrs.get("type") == "Parcel"]


def _centrality(graph: nx.MultiDiGraph) -> dict[str, dict[str, float]]:
    if graph.number_of_nodes() == 0:
        return {}
    ug = graph.to_undirected()
    pagerank = nx.pagerank(ug)
    betweenness = nx.betweenness_centrality(ug, normalized=True)
    try:
        eigen = nx.eigenvector_centrality(ug, max_iter=500)
    except Exception:
        eigen = {n: 0.0 for n in ug.nodes()}

    out = {}
    for node in ug.nodes():
        out[node] = {
            "pagerank": float(pagerank.get(node, 0.0)),
            "betweenness": float(betweenness.get(node, 0.0)),
            "eigenvector": float(eigen.get(node, 0.0)),
        }
    return out


def _cycle_patterns(graph: nx.MultiDiGraph) -> list[list[str]]:
    company_like = [
        n for n, d in graph.nodes(data=True)
        if d.get("type") in {"LLC", "Corporation", "Company", "Trust"}
    ]
    sub = graph.subgraph(company_like).copy()
    scc = [sorted(list(comp)) for comp in nx.strongly_connected_components(sub) if len(comp) > 1]
    scc.sort(key=len, reverse=True)
    return scc


def _shared_address_clusters(graph: nx.MultiDiGraph) -> list[dict]:
    addr_to_entities = defaultdict(set)
    for u, v, d in graph.edges(data=True):
        if d.get("type") != "REGISTERED_AT":
            continue
        if graph.nodes[v].get("type") == "Address":
            addr_to_entities[v].add(u)
    rows = [
        {
            "address": addr,
            "entity_count": len(entities),
            "entities": sorted(entities),
        }
        for addr, entities in addr_to_entities.items()
        if len(entities) >= 2
    ]
    rows.sort(key=lambda x: x["entity_count"], reverse=True)
    return rows


def infer_control(graph_store, threshold: float = 0.5, max_depth: int = 4) -> dict:
    graph = graph_store.graph
    controllers = _controller_candidates(graph)
    assets = _asset_nodes(graph)

    centrality = _centrality(graph)
    networks = []

    for controller in controllers:
        controlled_assets = []
        total_score = 0.0

        for asset in assets:
            if controller == asset:
                continue
            try:
                paths = list(nx.all_simple_paths(graph, source=controller, target=asset, cutoff=max_depth))
            except Exception:
                paths = []
            if not paths:
                continue
            best = max((_path_weight(graph, p) for p in paths), default=0.0)
            if best <= 0:
                continue
            total_score += best
            if best >= threshold:
                controlled_assets.append({"asset": asset, "score": round(best, 4)})

        if not controlled_assets:
            continue

        confidence = min(1.0, total_score / max(len(controlled_assets), 1))
        networks.append(
            {
                "controller": controller,
                "confidence": round(confidence, 4),
                "controlled_assets": controlled_assets,
                "asset_count": len(controlled_assets),
                "centrality": centrality.get(controller, {}),
                "signal": (
                    "strong control" if confidence > 0.7 else
                    "possible control" if confidence >= 0.5 else
                    "weak signal"
                ),
            }
        )

    networks.sort(key=lambda x: (x["confidence"], x["asset_count"]), reverse=True)

    return {
        "controllers": networks,
        "cycles": _cycle_patterns(graph),
        "shared_address_clusters": _shared_address_clusters(graph),
    }
