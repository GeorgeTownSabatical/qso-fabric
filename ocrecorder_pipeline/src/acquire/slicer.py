"""Query slicing utilities for bounded, resumable collection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class QuerySlice:
    surname: str
    date_from: str
    date_to: str
    doc_type: str | None = None
    page: int = 1


def hash_slice(q: QuerySlice) -> str:
    raw = f"{q.surname}|{q.date_from}|{q.date_to}|{q.doc_type or ''}|{q.page}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _quarter_ranges(year: int) -> list[tuple[str, str]]:
    return [
        (f"{year}-01-01", f"{year}-03-31"),
        (f"{year}-04-01", f"{year}-06-30"),
        (f"{year}-07-01", f"{year}-09-30"),
        (f"{year}-10-01", f"{year}-12-31"),
    ]


def generate_query_slices(
    surnames: Iterable[str],
    year_start: int,
    year_end: int,
    *,
    use_quarters: bool = False,
    doc_types: list[str] | None = None,
) -> list[QuerySlice]:
    if year_end < year_start:
        raise ValueError("year_end must be >= year_start")

    normalized_surnames = sorted({s.strip().upper() for s in surnames if s.strip()})
    if not normalized_surnames:
        return []

    doc_types_norm = [d.strip().upper() for d in (doc_types or []) if d.strip()]
    doc_types_norm = doc_types_norm or [None]

    slices: list[QuerySlice] = []
    for surname in normalized_surnames:
        for year in range(year_start, year_end + 1):
            date_windows = _quarter_ranges(year) if use_quarters else [(f"{year}-01-01", f"{year}-12-31")]
            for date_from, date_to in date_windows:
                for doc_type in doc_types_norm:
                    slices.append(
                        QuerySlice(
                            surname=surname,
                            date_from=date_from,
                            date_to=date_to,
                            doc_type=doc_type,
                            page=1,
                        )
                    )
    return slices


def save_slices(path: Path, slices: list[QuerySlice]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{**asdict(s), "slice_hash": hash_slice(s)} for s in slices]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_slices(path: Path) -> list[QuerySlice]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[QuerySlice] = []
    for item in data:
        out.append(
            QuerySlice(
                surname=str(item["surname"]),
                date_from=str(item["date_from"]),
                date_to=str(item["date_to"]),
                doc_type=item.get("doc_type"),
                page=int(item.get("page", 1)),
            )
        )
    return out
