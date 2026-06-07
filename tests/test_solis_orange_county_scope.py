from __future__ import annotations

import sqlite3
from pathlib import Path

from tools import solis_orange_county_scope


def test_id_builders_are_deterministic() -> None:
    assert solis_orange_county_scope._solis_apn_id("00100001") == "solis:oc:apn:00100001"
    assert (
        solis_orange_county_scope._solis_transition_id("00100001", 1, 2)
        == "solis:oc:transition:00100001:000001:000002"
    )


def test_extract_event_date_handles_mixed_numeric_formats() -> None:
    assert (
        solis_orange_county_scope._extract_event_date({"SaleRecordDate": 719107200000})
        == "1992-10-15"
    )
    assert (
        solis_orange_county_scope._extract_event_date({"RecordDate": 20240131})
        == "2024-01-31"
    )


def test_build_scope_generates_states_transitions_and_anomalies(tmp_path: Path) -> None:
    db_path = tmp_path / "scope.sqlite3"
    conn = sqlite3.connect(db_path)
    try:
        solis_orange_county_scope._ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO apn_records (objectid, assessment_no, assessment_no_norm)
            VALUES (1, '001-000-01', '00100001')
            """
        )

        conn.executemany(
            """
            INSERT INTO solis_source_catalog (source_id, endpoint, record_kind, updated_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("parcel_attributes", "https://example.test/1", "parcel_attribute_snapshot", "2026-01-01T00:00:00Z"),
                ("doc_road_deed", "https://example.test/2", "road_deed", "2026-01-01T00:00:00Z"),
            ],
        )

        rows = [
            (
                "parcel_attributes",
                1,
                "solis:oc:fragment:parcel_attributes:1",
                "hash-1",
                "001-000-01",
                "00100001",
                "LL1",
                None,
                "DOC-1",
                "parcel_attribute_snapshot",
                "2020-01-01",
                "{}",
                "2026-01-01T00:00:00Z",
            ),
            (
                "parcel_attributes",
                2,
                "solis:oc:fragment:parcel_attributes:2",
                "hash-2",
                "001-000-01",
                "00100001",
                "LL2",
                None,
                "DOC-2",
                "parcel_attribute_snapshot",
                "2020-02-01",
                "{}",
                "2026-01-01T00:00:00Z",
            ),
            (
                "parcel_attributes",
                3,
                "solis:oc:fragment:parcel_attributes:3",
                "hash-3",
                "001-000-01",
                "00100001",
                "LL3",
                None,
                "DOC-3",
                "parcel_attribute_snapshot",
                "2020-03-01",
                "{}",
                "2026-01-01T00:00:00Z",
            ),
            (
                "doc_road_deed",
                4,
                "solis:oc:fragment:doc_road_deed:4",
                "hash-4",
                "001-000-01",
                "00100001",
                "LL4",
                "MAP-1",
                "DOC-4",
                "Road Deed",
                "2020-04-01",
                "{}",
                "2026-01-01T00:00:00Z",
            ),
        ]
        conn.executemany(
            """
            INSERT INTO solis_source_fragments (
                source_id,
                source_objectid,
                solis_fragment_id,
                fragment_hash,
                apn,
                apn_norm,
                legal_lot_id,
                map_num,
                doc_num,
                doc_type,
                event_date,
                payload_json,
                fetched_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    summary = solis_orange_county_scope.build_scope(db_path)
    assert summary["solis_apn_count"] == 1
    assert summary["state_count"] == 4
    assert summary["transition_count"] == 3
    assert summary["anomaly_count"] >= 2

    conn = sqlite3.connect(db_path)
    try:
        scope_row = conn.execute(
            """
            SELECT fragment_count, state_count, transition_count, anomaly_count, has_easement_activity
            FROM solis_apn_scope
            WHERE assessment_no_norm = '00100001'
            """
        ).fetchone()
        assert scope_row is not None
        assert scope_row[0] == 4
        assert scope_row[1] == 4
        assert scope_row[2] == 3
        assert scope_row[3] >= 2
        assert scope_row[4] == 1
    finally:
        conn.close()


def test_build_scope_preserves_live_anomalies(tmp_path: Path) -> None:
    db_path = tmp_path / "scope.sqlite3"
    conn = sqlite3.connect(db_path)
    try:
        solis_orange_county_scope._ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO apn_records (objectid, assessment_no, assessment_no_norm)
            VALUES (1, '001-000-01', '00100001')
            """
        )
        conn.execute(
            """
            INSERT INTO solis_source_fragments (
                source_id,
                source_objectid,
                solis_fragment_id,
                fragment_hash,
                apn,
                apn_norm,
                legal_lot_id,
                map_num,
                doc_num,
                doc_type,
                event_date,
                payload_json,
                fetched_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "parcel_attributes",
                1,
                "solis:oc:fragment:parcel_attributes:1",
                "hash-1",
                "001-000-01",
                "00100001",
                "LL1",
                "MAP-1",
                "DOC-1",
                "parcel_attribute_snapshot",
                "2020-01-01",
                "{}",
                "2026-01-01T00:00:00Z",
            ),
        )
        conn.execute(
            """
            INSERT INTO solis_apn_anomaly (
                solis_anomaly_id,
                solis_apn_id,
                anomaly_type,
                severity,
                signal_value,
                details_json,
                detected_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "solis:oc:anomaly:live:test",
                "solis:oc:apn:00100001",
                "live_test_signal",
                "low",
                1.0,
                "{}",
                "2026-01-01T00:00:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    summary = solis_orange_county_scope.build_scope(db_path)
    assert summary["state_count"] == 1

    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM solis_apn_anomaly WHERE anomaly_type = 'live_test_signal'"
        ).fetchone()[0]
        assert count == 1
    finally:
        conn.close()
