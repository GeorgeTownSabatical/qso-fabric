"""Timeline report builder for parcel transfer history."""

from __future__ import annotations


def build_parcel_timeline(graph_store, parcel: str) -> list[dict]:
    timeline = []
    graph = graph_store.graph
    for u, v, d in graph.edges(data=True):
        if parcel not in {u, v}:
            continue
        if d.get("type") not in {"TRANSFERRED", "OWNED_BY", "OWNS"}:
            continue
        timeline.append(
            {
                "source": u,
                "target": v,
                "type": d.get("type"),
                "date": d.get("date") or d.get("from_ts") or "",
                "document": d.get("document", ""),
            }
        )
    timeline.sort(key=lambda x: x["date"])
    return timeline
