"""Parcel-level suspicion scoring."""

from __future__ import annotations

import numpy as np
import pandas as pd

from normalize.names import extract_surname


def compute_parcel_scores(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    if df.empty:
        return pd.DataFrame(columns=["apn", "doc_count", "unique_surnames", "same_notary_ratio", "velocity", "score"])

    for apn, sub in df.groupby("apn"):
        sub = sub.sort_values("record_date")
        if len(sub) < 2:
            continue

        surnames = pd.concat(
            [
                sub["grantor"].map(extract_surname),
                sub["grantee"].map(extract_surname),
            ],
            ignore_index=True,
        )
        unique_surnames = int(surnames[surnames.str.len() > 0].nunique())

        same_notary_ratio = 0.0
        if "notary" in sub.columns and sub["notary"].notna().any():
            same_notary_ratio = float(sub["notary"].value_counts(normalize=True).max())

        span_days = max(int((sub["record_date"].max() - sub["record_date"].min()).days), 1)
        velocity = float(len(sub) / (span_days / 365.25))

        score = (
            0.35 * np.log1p(len(sub)) +
            0.25 * np.log1p(velocity) +
            0.20 * same_notary_ratio +
            0.20 * (1 / max(unique_surnames, 1))
        )

        rows.append(
            {
                "apn": apn,
                "doc_count": int(len(sub)),
                "unique_surnames": unique_surnames,
                "same_notary_ratio": same_notary_ratio,
                "velocity": velocity,
                "score": float(score),
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values("score", ascending=False)
