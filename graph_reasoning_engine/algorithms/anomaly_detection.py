"""Structural anomaly detection on graph patterns."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import networkx as nx


def _parse_date(value):
    try:
        return datetime.fromisoformat(str(value)) if value else None
    except Exception:
        return None


def detect_anomalies(graph) -> dict:
    anomalies = {
        "rapid_transfer_parcels": [],
        "ownership_cycles": [],
        "dense_llc_rings": [],
    }

    parcel_dates = defaultdict(list)
    for u, v, d in graph.edges(data=True):
        if d.get("type") in {"TRANSFERRED", "OWNED_BY"}:
            dt = _parse_date(d.get("date"))
            if dt is None:
                continue
            parcel = v if graph.nodes.get(v, {}).get("type") == "Parcel" else u
            if graph.nodes.get(parcel, {}).get("type") == "Parcel":
                parcel_dates[parcel].append(dt)

    for parcel, dates in parcel_dates.items():
        dates.sort()
        if len(dates) < 3:
            continue
        for i in range(len(dates) - 2):
            if (dates[i + 2] - dates[i]).days <= 365:
                anomalies["rapid_transfer_parcels"].append(parcel)
                break

    company_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") in {"LLC", "Company", "Corporation", "Trust"}]
    sub = graph.subgraph(company_nodes).copy()
    scc = [sorted(list(c)) for c in nx.strongly_connected_components(sub) if len(c) > 1]
    anomalies["ownership_cycles"] = scc
    anomalies["dense_llc_rings"] = [c for c in scc if len(c) >= 3]

    return anomalies
