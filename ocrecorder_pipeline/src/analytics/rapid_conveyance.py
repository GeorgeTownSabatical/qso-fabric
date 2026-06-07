"""Rapid multi-deed conveyance detection."""

from __future__ import annotations

import pandas as pd


def detect_rapid_conveyances(df: pd.DataFrame, *, max_days: int = 30, min_docs: int = 3) -> pd.DataFrame:
    alerts: list[dict] = []
    if df.empty:
        return pd.DataFrame(columns=["apn", "window_start", "window_end", "docs_in_window", "deed_docs", "unique_parties", "same_notary_ratio", "doc_numbers"])

    ordered = df.sort_values("record_date")
    for apn, sub in ordered.groupby("apn"):
        sub = sub.sort_values("record_date").reset_index(drop=True)
        if len(sub) < min_docs:
            continue

        start = 0
        for i in range(len(sub)):
            while sub.loc[i, "record_date"] - sub.loc[start, "record_date"] > pd.Timedelta(days=max_days):
                start += 1
            window = sub.iloc[start : i + 1]
            deed_like = window["doc_type"].fillna("").str.contains("DEED|TRUST|QUITCLAIM|GRANT", case=False, regex=True)
            if int(deed_like.sum()) < min_docs:
                continue

            party_series = pd.concat([window["grantor"], window["grantee"]], ignore_index=True)
            notary_ratio = 0.0
            if window["notary"].notna().any():
                notary_ratio = float(window["notary"].value_counts(normalize=True).max())

            alerts.append(
                {
                    "apn": apn,
                    "window_start": window["record_date"].min(),
                    "window_end": window["record_date"].max(),
                    "docs_in_window": int(len(window)),
                    "deed_docs": int(deed_like.sum()),
                    "unique_parties": int(party_series.nunique()),
                    "same_notary_ratio": notary_ratio,
                    "doc_numbers": "|".join(window["doc_number"].astype(str).tolist()),
                }
            )

    out = pd.DataFrame(alerts)
    if out.empty:
        return out
    return out.sort_values(["deed_docs", "docs_in_window", "same_notary_ratio"], ascending=False)
