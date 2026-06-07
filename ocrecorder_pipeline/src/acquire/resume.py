"""Manifest helpers for restart-safe collection."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from acquire.slicer import QuerySlice, hash_slice


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return json.loads(text)


def write_manifest(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def append_manifest_record(path: Path, *, query_slice: QuerySlice, status: str, raw_file: str | None = None, notes: str = "") -> None:
    records = read_manifest(path)
    records.append(
        {
            "ts": utc_now(),
            "slice": {
                "surname": query_slice.surname,
                "date_from": query_slice.date_from,
                "date_to": query_slice.date_to,
                "doc_type": query_slice.doc_type,
                "page": query_slice.page,
                "slice_hash": hash_slice(query_slice),
            },
            "status": status,
            "raw_file": raw_file,
            "notes": notes,
        }
    )
    write_manifest(path, records)


def completed_hashes(path: Path) -> set[str]:
    return {
        str(r.get("slice", {}).get("slice_hash"))
        for r in read_manifest(path)
        if str(r.get("status", "")).lower() == "ok"
    }
