"""Detect intentionally layered ownership obfuscation patterns."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import networkx as nx


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _chain_depth_scores(graph: nx.MultiDiGraph) -> dict[str, float]:
    parcels = [n for n, d in graph.nodes(data=True) if d.get("type") == "Parcel"]
    entities = [n for n, d in graph.nodes(data=True) if d.get("type") in {"Person", "Trust", "LLC", "Corporation", "Company"}]
    scores = defaultdict(float)

    for e in entities:
        depths = []
        for p in parcels:
            if e == p:
                continue
            try:
                paths = list(nx.all_simple_paths(graph, source=e, target=p, cutoff=7))
            except Exception:
                continue
            for path in paths:
                depths.append(len(path) - 2)  # intermediary entity count approximation
        if not depths:
            continue
        avg_depth = sum(depths) / len(depths)
        # 1-2 normal, 3-4 complex, 5+ suspicious
        if avg_depth <= 2:
            score = 0.2
        elif avg_depth <= 4:
            score = 0.55
        else:
            score = 0.9
        scores[e] = score
    return scores


def _structural_similarity(graph: nx.MultiDiGraph) -> dict[str, float]:
    parcels = [n for n, d in graph.nodes(data=True) if d.get("type") == "Parcel"]
    entities = [n for n, d in graph.nodes(data=True) if d.get("type") in {"Person", "Trust", "LLC", "Corporation", "Company"}]
    scores = defaultdict(float)

    for e in entities:
        patterns = []
        for p in parcels:
            try:
                paths = list(nx.all_simple_paths(graph, source=e, target=p, cutoff=6))
            except Exception:
                continue
            for path in paths[:3]:
                sig = tuple(graph.nodes[n].get("type", "X") for n in path)
                patterns.append(sig)
        if not patterns:
            continue
        counts = Counter(patterns)
        dominant_ratio = max(counts.values()) / len(patterns)
        scores[e] = dominant_ratio
    return scores


def _address_concentration(graph: nx.MultiDiGraph) -> dict[str, float]:
    entity_addresses = defaultdict(set)
    for u, v, d in graph.edges(data=True):
        if d.get("type") == "REGISTERED_AT":
            entity_addresses[u].add(v)
    address_counts = Counter(addr for addrs in entity_addresses.values() for addr in addrs)

    scores = {}
    for entity, addrs in entity_addresses.items():
        if not addrs:
            scores[entity] = 0.0
            continue
        max_share = max(address_counts[a] for a in addrs)
        # normalize to 0..1 using cap 10+ entities at same address
        scores[entity] = min(1.0, max_share / 10.0)
    return scores


def _entity_burst_score(graph: nx.MultiDiGraph) -> dict[str, float]:
    # Burst signal by clustering formation dates around each controller's immediate neighbors.
    scores = defaultdict(float)
    for node, attrs in graph.nodes(data=True):
        if attrs.get("type") not in {"Person", "Trust", "LLC", "Corporation", "Company"}:
            continue
        dates = []
        for nbr in graph.neighbors(node):
            d = _parse_date(graph.nodes[nbr].get("formation_date"))
            if d:
                dates.append(d)
        if len(dates) < 2:
            scores[node] = 0.0
            continue
        dates.sort()
        span_days = (dates[-1] - dates[0]).days
        scores[node] = 1.0 if span_days <= 7 else 0.7 if span_days <= 30 else 0.3
    return scores


def _transfer_velocity_score(graph: nx.MultiDiGraph) -> dict[str, float]:
    parcel_dates = defaultdict(list)
    for u, v, d in graph.edges(data=True):
        if d.get("type") not in {"TRANSFERRED", "OWNED_BY"}:
            continue
        date = _parse_date(d.get("date"))
        if not date:
            continue
        parcel = v if graph.nodes.get(v, {}).get("type") == "Parcel" else u
        if graph.nodes.get(parcel, {}).get("type") != "Parcel":
            continue
        parcel_dates[parcel].append(date)

    entity_scores = defaultdict(float)
    for parcel, dates in parcel_dates.items():
        dates.sort()
        score = 0.0
        for i in range(len(dates)):
            for j in range(i + 2, len(dates)):
                days = (dates[j] - dates[i]).days
                if days <= 365:
                    score = max(score, 1.0)
                elif days <= 730:
                    score = max(score, 0.7)
        if score == 0.0:
            continue
        for pred in graph.predecessors(parcel):
            entity_scores[pred] = max(entity_scores[pred], score)
        for succ in graph.successors(parcel):
            entity_scores[succ] = max(entity_scores[succ], score)
    return entity_scores


def _cycle_score(graph: nx.MultiDiGraph) -> dict[str, float]:
    company_like = [n for n, d in graph.nodes(data=True) if d.get("type") in {"Trust", "LLC", "Corporation", "Company"}]
    sub = graph.subgraph(company_like).copy()
    scores = defaultdict(float)
    for comp in nx.strongly_connected_components(sub):
        if len(comp) <= 1:
            continue
        component_score = min(1.0, len(comp) / 5.0)
        for n in comp:
            scores[n] = max(scores[n], component_score)
    return scores


def detect(graph_store) -> list[dict]:
    graph = graph_store.graph
    depth = _chain_depth_scores(graph)
    structural = _structural_similarity(graph)
    address = _address_concentration(graph)
    burst = _entity_burst_score(graph)
    velocity = _transfer_velocity_score(graph)
    cycles = _cycle_score(graph)

    entities = {n for n, d in graph.nodes(data=True) if d.get("type") in {"Person", "Trust", "LLC", "Corporation", "Company"}}
    out = []

    for entity in sorted(entities):
        score = (
            0.25 * depth.get(entity, 0.0)
            + 0.20 * structural.get(entity, 0.0)
            + 0.20 * address.get(entity, 0.0)
            + 0.20 * velocity.get(entity, 0.0)
            + 0.15 * burst.get(entity, 0.0)
        )
        score = max(score, cycles.get(entity, 0.0) * 0.8)

        if score < 0.4:
            cls = "normal structure"
        elif score < 0.7:
            cls = "complex network"
        else:
            cls = "likely obfuscation"

        controlled_parcels = sorted({n for n in graph.neighbors(entity) if graph.nodes[n].get("type") == "Parcel"})

        out.append(
            {
                "entity": entity,
                "obfuscation_score": round(min(1.0, score), 4),
                "classification": cls,
                "chain_depth_score": round(depth.get(entity, 0.0), 4),
                "structural_similarity": round(structural.get(entity, 0.0), 4),
                "address_concentration": round(address.get(entity, 0.0), 4),
                "transfer_velocity": round(velocity.get(entity, 0.0), 4),
                "entity_burst": round(burst.get(entity, 0.0), 4),
                "cycle_score": round(cycles.get(entity, 0.0), 4),
                "controlled_parcels": controlled_parcels,
            }
        )

    out.sort(key=lambda x: x["obfuscation_score"], reverse=True)
    return out
