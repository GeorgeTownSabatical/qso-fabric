"""Parcel timeline export utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from analytics.title_chain import parcel_timeline


def export_parcel_timeline(df: pd.DataFrame, apn: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timeline = parcel_timeline(df, apn)
    timeline.to_csv(output_path, index=False)
    return output_path
