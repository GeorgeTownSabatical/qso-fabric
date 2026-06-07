"""Cluster heatmap export (table-based)."""

from __future__ import annotations

from pathlib import Path
import csv


def export_cluster_table(cluster_rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cluster_rows:
        path.write_text("", encoding="utf-8")
        return path
    keys = sorted(cluster_rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        for row in cluster_rows:
            writer.writerow(row)
    return path
