"""Canonical record normalization for analytics."""

from __future__ import annotations

import pandas as pd

from normalize.apn import normalize_apn
from normalize.names import entity_type, extract_surname, normalize_text


REQUIRED_COLUMNS = ["doc_number", "record_date", "doc_type", "apn", "grantor", "grantee", "notary"]


def normalize_records(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    out = df.copy()
    out["record_date"] = pd.to_datetime(out["record_date"], errors="coerce")

    out["apn_raw"] = out["apn"].astype(str)
    out["apn"] = out["apn"].map(normalize_apn)

    out["grantor_raw"] = out["grantor"].astype(str)
    out["grantee_raw"] = out["grantee"].astype(str)
    out["notary_raw"] = out["notary"].astype(str)

    out["grantor"] = out["grantor"].map(normalize_text)
    out["grantee"] = out["grantee"].map(normalize_text)
    out["notary"] = out["notary"].map(normalize_text)

    out["grantor_surname"] = out["grantor"].map(extract_surname)
    out["grantee_surname"] = out["grantee"].map(extract_surname)

    out["grantor_entity_type"] = out["grantor"].map(entity_type)
    out["grantee_entity_type"] = out["grantee"].map(entity_type)
    return out
