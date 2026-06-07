"""Surname-level anomaly scoring."""

from __future__ import annotations

import numpy as np
import pandas as pd

from normalize.names import extract_surname


def _party_frame(df: pd.DataFrame) -> pd.DataFrame:
    left = df[["doc_number", "record_date", "apn", "notary", "grantor"]].copy()
    left = left.rename(columns={"grantor": "party_name"})
    right = df[["doc_number", "record_date", "apn", "notary", "grantee"]].copy()
    right = right.rename(columns={"grantee": "party_name"})
    out = pd.concat([left, right], ignore_index=True)
    out["surname"] = out["party_name"].map(extract_surname)
    out = out[out["surname"].astype(str).str.len() > 0]
    return out


def compute_surname_summary(df: pd.DataFrame) -> pd.DataFrame:
    pf = _party_frame(df)
    if pf.empty:
        return pd.DataFrame(
            columns=[
                "surname",
                "doc_count",
                "unique_apns",
                "unique_notaries",
                "first_date",
                "last_date",
                "apn_concentration",
                "notary_concentration",
                "span_days",
                "velocity",
                "anomaly_score",
                "top_notary",
            ]
        )

    grp = pf.groupby("surname")
    summary = grp.agg(
        doc_count=("doc_number", "count"),
        unique_apns=("apn", "nunique"),
        unique_notaries=("notary", "nunique"),
        first_date=("record_date", "min"),
        last_date=("record_date", "max"),
    )

    summary["apn_concentration"] = 1 - (summary["unique_apns"] / summary["doc_count"]).clip(upper=1)
    summary["notary_concentration"] = 1 - (summary["unique_notaries"] / summary["doc_count"]).clip(upper=1)
    summary["span_days"] = (summary["last_date"] - summary["first_date"]).dt.days.clip(lower=1)
    summary["velocity"] = summary["doc_count"] / (summary["span_days"] / 365.25)

    summary["anomaly_score"] = (
        0.40 * np.log1p(summary["doc_count"]) +
        0.25 * summary["apn_concentration"] +
        0.20 * summary["notary_concentration"] +
        0.15 * np.log1p(summary["velocity"])
    )

    notary_mode = (
        pf.groupby("surname")["notary"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else "")
        .rename("top_notary")
    )
    summary = summary.join(notary_mode, how="left")

    summary = summary.reset_index().sort_values("anomaly_score", ascending=False)
    return summary
