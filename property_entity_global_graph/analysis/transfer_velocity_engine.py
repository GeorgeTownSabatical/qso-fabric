"""Transfer velocity detector for parcel events."""

from __future__ import annotations

from datetime import datetime


def _parse_date(text: str) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def detect(graph_store, min_transfers: int = 3, window_days: int = 730) -> list[dict]:
    graph = graph_store.graph
    parcel_events = {}
    for u, v, d in graph.edges(data=True):
        if d.get("type") not in {"TRANSFERRED", "OWNED_BY"}:
            continue
        parcel = v if isinstance(v, str) and "-" in v and v.count("-") >= 2 else u
        dt = _parse_date(str(d.get("date", "")))
        if dt is None:
            continue
        parcel_events.setdefault(parcel, []).append(dt)

    findings = []
    for parcel, dates in parcel_events.items():
        dates.sort()
        for i in range(len(dates)):
            for j in range(i + min_transfers - 1, len(dates)):
                delta = (dates[j] - dates[i]).days
                if delta <= window_days:
                    findings.append(
                        {
                            "parcel": parcel,
                            "transfer_count": j - i + 1,
                            "from": dates[i].date().isoformat(),
                            "to": dates[j].date().isoformat(),
                            "window_days": delta,
                        }
                    )
                    break
    return sorted(findings, key=lambda x: (x["transfer_count"], -x["window_days"]), reverse=True)
