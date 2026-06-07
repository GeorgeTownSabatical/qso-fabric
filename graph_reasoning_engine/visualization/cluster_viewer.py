"""Cluster visualization/export utilities."""

from __future__ import annotations

import csv
from pathlib import Path


def export_clusters(clusters: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["cluster_id", "size", "members"])
        for c in clusters:
            writer.writerow([c["cluster_id"], c["size"], "|".join(c["members"])])
    return path
