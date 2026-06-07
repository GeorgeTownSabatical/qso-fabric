import pandas as pd

from analytics.parcel_scores import compute_parcel_scores
from analytics.rapid_conveyance import detect_rapid_conveyances
from analytics.surname_stats import compute_surname_summary
from normalize.entities import normalize_records


def _sample_df() -> pd.DataFrame:
    rows = [
        ["2024-1", "2024-01-01", "GRANT DEED", "40511217", "SMITH, JOHN", "DOE, JANE", "R LOPEZ"],
        ["2024-2", "2024-01-05", "DEED OF TRUST", "40511217", "DOE, JANE", "SMITH FAMILY TRUST", "R LOPEZ"],
        ["2024-3", "2024-01-20", "QUITCLAIM DEED", "40511217", "SMITH FAMILY TRUST", "SMITH, JOHN", "R LOPEZ"],
        ["2024-4", "2024-03-01", "GRANT DEED", "40511218", "LEE, MIN", "KIM, JI", "T CHEN"],
    ]
    return pd.DataFrame(rows, columns=["doc_number", "record_date", "doc_type", "apn", "grantor", "grantee", "notary"])


def test_surname_summary_nonempty():
    df = normalize_records(_sample_df())
    out = compute_surname_summary(df)
    assert not out.empty
    assert "anomaly_score" in out.columns


def test_rapid_conveyance_alerts():
    df = normalize_records(_sample_df())
    alerts = detect_rapid_conveyances(df, max_days=30, min_docs=3)
    assert not alerts.empty
    assert alerts.iloc[0]["apn"] == "405-112-17"


def test_parcel_scores_nonempty():
    df = normalize_records(_sample_df())
    out = compute_parcel_scores(df)
    assert not out.empty
    assert "score" in out.columns
