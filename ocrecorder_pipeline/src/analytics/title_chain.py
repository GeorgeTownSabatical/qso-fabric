"""Title chain timeline helpers."""

from __future__ import annotations

import pandas as pd


def parcel_timeline(df: pd.DataFrame, apn: str) -> pd.DataFrame:
    sub = df[df["apn"] == apn].copy()
    if sub.empty:
        return pd.DataFrame(columns=["record_date", "doc_number", "doc_type", "grantor", "grantee", "notary"])
    return sub.sort_values(["record_date", "doc_number"])[
        ["record_date", "doc_number", "doc_type", "grantor", "grantee", "notary"]
    ]
