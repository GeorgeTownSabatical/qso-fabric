from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools import solis_orange_county_apn_db
from tools import solis_orange_county_kaggle_export
from tools import solis_orange_county_scope


def _seed_scope_database(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        solis_orange_county_apn_db._ensure_schema(conn)
        solis_orange_county_scope._ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO apn_records (
                objectid,
                assessment_no,
                assessment_no_norm,
                legal_lot_id,
                doc_num,
                map_num,
                site_address,
                site_city_state,
                site_zip5,
                assd_amt,
                land_val,
                improved_val,
                gplu_code,
                gplu_desc,
                zclass,
                fetched_at_utc,
                source_endpoint
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "001-000-01",
                "00100001",
                "LL-1",
                "DOC-1",
                "MAP-1",
                "1 Main St",
                "Irvine, CA",
                "92602",
                120000.0,
                80000.0,
                40000.0,
                "R",
                "Residential",
                "R1",
                "2026-02-28T00:00:00Z",
                "https://example.test/FeatureServer/0",
            ),
        )
        conn.execute(
            """
            INSERT INTO solis_apn (
                solis_apn_id,
                assessment_no,
                assessment_no_norm,
                first_event_date,
                last_event_date,
                fragment_count,
                legal_lot_count,
                has_easement_activity,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "solis:oc:apn:00100001",
                "001-000-01",
                "00100001",
                "2020-01-01",
                "2020-02-01",
                2,
                1,
                0,
                "2026-02-28T00:00:00Z",
                "2026-02-28T00:00:00Z",
            ),
        )
        conn.executemany(
            """
            INSERT INTO solis_apn_state (
                solis_state_id,
                solis_apn_id,
                state_sequence,
                event_date,
                source_id,
                source_objectid,
                doc_num,
                map_num,
                legal_lot_id,
                solis_fragment_id,
                state_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "solis:oc:state:00100001:000001",
                    "solis:oc:apn:00100001",
                    1,
                    "2020-01-01",
                    "parcel_attributes",
                    1,
                    "DOC-1",
                    "MAP-1",
                    "LL-1",
                    "solis:oc:fragment:parcel_attributes:1",
                    "hash-1",
                ),
                (
                    "solis:oc:state:00100001:000002",
                    "solis:oc:apn:00100001",
                    2,
                    "2020-02-01",
                    "doc_road_deed",
                    2,
                    "DOC-2",
                    "MAP-2",
                    "LL-1",
                    "solis:oc:fragment:doc_road_deed:2",
                    "hash-2",
                ),
            ],
        )
        conn.execute(
            """
            INSERT INTO solis_apn_transition (
                solis_transition_id,
                solis_apn_id,
                from_state_id,
                to_state_id,
                transition_days,
                trigger_doc_num,
                trigger_map_num
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "solis:oc:transition:00100001:000001:000002",
                "solis:oc:apn:00100001",
                "solis:oc:state:00100001:000001",
                "solis:oc:state:00100001:000002",
                31,
                "DOC-2",
                "MAP-2",
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
                "solis:oc:anomaly:00100001:test",
                "solis:oc:apn:00100001",
                "historical_density",
                "medium",
                0.75,
                "{\"row_count\":2}",
                "2026-02-28T00:00:00Z",
            ),
        )
        conn.execute(
            """
            INSERT INTO solis_apn_scope (
                solis_apn_id,
                assessment_no,
                assessment_no_norm,
                fragment_count,
                state_count,
                transition_count,
                anomaly_count,
                first_event_date,
                last_event_date,
                has_easement_activity,
                built_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "solis:oc:apn:00100001",
                "001-000-01",
                "00100001",
                2,
                2,
                1,
                1,
                "2020-01-01",
                "2020-02-01",
                0,
                "2026-02-28T00:00:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_export_release_writes_versioned_jsonl_datasets(tmp_path: Path) -> None:
    db_path = tmp_path / "apn.sqlite3"
    _seed_scope_database(db_path)

    output_root = tmp_path / "kaggle_exports"
    manifest = solis_orange_county_kaggle_export.export_release(
        db_path=db_path,
        output_root=output_root,
        release_id="20260228T000000Z",
        format_name="jsonl",
        kaggle_id="",
        kaggle_title="",
        publish_kaggle=False,
        create_kaggle=False,
        kaggle_message="",
    )

    release_dir = output_root / "20260228T000000Z"
    assert release_dir.exists()
    assert manifest["format"] == "jsonl"
    assert len(manifest["datasets"]) == 5
    assert manifest["datasets"][0]["dataset_name"] == "oc_apn_core"
    assert manifest["datasets"][0]["row_count"] == 1
    assert manifest["datasets"][-1]["dataset_name"] == "oc_risk_snapshot"

    apn_core_path = release_dir / "oc_apn_core.jsonl"
    lines = apn_core_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["assessment_no"] == "001-000-01"
    assert record["anomaly_count"] == 1

    manifest_path = release_dir / "manifest.json"
    manifest_on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_on_disk["release_id"] == "20260228T000000Z"
    assert manifest_on_disk["source_db"]["path"] == str(db_path)
    assert manifest_on_disk["consistency"]["solis_apn_state_count"] == 2

    risk_path = release_dir / "oc_risk_snapshot.jsonl"
    risk_rows = risk_path.read_text(encoding="utf-8").splitlines()
    assert len(risk_rows) == 1
    risk = json.loads(risk_rows[0])
    assert risk["state_span_days"] == 31
    assert risk["recent_event_count_365d"] == 2
    assert risk["short_transition_count_90d"] == 1
    assert risk["distinct_source_count"] == 2
    assert risk["risk_bucket"] in {"low", "elevated", "coordinated", "structured", "critical"}


def test_export_release_writes_kaggle_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "apn.sqlite3"
    _seed_scope_database(db_path)

    output_root = tmp_path / "kaggle_exports"
    manifest = solis_orange_county_kaggle_export.export_release(
        db_path=db_path,
        output_root=output_root,
        release_id="20260228T010000Z",
        format_name="jsonl",
        kaggle_id="alistaire/oc-parcel-intel-test",
        kaggle_title="OC Parcel Intel Test",
        publish_kaggle=False,
        create_kaggle=False,
        kaggle_message="",
    )

    metadata_path = output_root / "20260228T010000Z" / "dataset-metadata.json"
    assert metadata_path.exists()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["id"] == "alistaire/oc-parcel-intel-test"
    assert metadata["title"] == "OC Parcel Intel Test"
    assert manifest["kaggle_metadata"]["kaggle_id"] == "alistaire/oc-parcel-intel-test"
