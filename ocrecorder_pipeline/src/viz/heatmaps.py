"""Matrix builders for heatmap-compatible outputs."""

from __future__ import annotations

import pandas as pd

from normalize.names import extract_surname


def build_surname_apn_density_matrix(df: pd.DataFrame, *, top_surnames: int = 100, top_apns: int = 200) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    tmp = df.copy()
    tmp["surname"] = tmp["grantor"].map(extract_surname)
    pivot = (
        tmp.groupby(["surname", "apn"])
        .size()
        .reset_index(name="n")
        .pivot(index="surname", columns="apn", values="n")
        .fillna(0)
    )

    if pivot.empty:
        return pivot

    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).head(top_surnames).index]
    pivot = pivot[pivot.sum(axis=0).sort_values(ascending=False).head(top_apns).index]
    return pivot


def compute_parcel_stats(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["apn", "doc_count", "surname_count", "first_date", "last_date", "span_days", "velocity"])

    tmp = df.copy()
    tmp["surname"] = tmp["grantor"].map(extract_surname)
    stats = (
        tmp.groupby("apn")
        .agg(
            doc_count=("doc_number", "count"),
            surname_count=("surname", "nunique"),
            first_date=("record_date", "min"),
            last_date=("record_date", "max"),
        )
        .reset_index()
    )
    stats["span_days"] = (stats["last_date"] - stats["first_date"]).dt.days.clip(lower=1)
    stats["velocity"] = stats["doc_count"] / (stats["span_days"] / 365.25)
    return stats
