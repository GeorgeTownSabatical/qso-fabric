from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools import solis_orange_county_apn_db


def test_normalize_apn() -> None:
    assert solis_orange_county_apn_db._normalize_apn("072-476-34") == "07247634"
    assert solis_orange_county_apn_db._normalize_apn(" 072 476 34 ") == "07247634"
    assert solis_orange_county_apn_db._normalize_apn("AB-01-99") == "AB0199"


def test_to_float_accepts_formatted_currency() -> None:
    assert solis_orange_county_apn_db._to_float("$11,257") == 11257.0
    assert solis_orange_county_apn_db._to_float("(1,234.50)") == -1234.5
    assert solis_orange_county_apn_db._to_float("  ") is None


def test_sync_apn_database_checkpoint_resume(tmp_path: Path) -> None:
    db_path = tmp_path / "apn.sqlite3"
    checkpoint_path = tmp_path / "checkpoint.json"
    summary_path = tmp_path / "summary.json"

    batches_first_run = {
        0: [
            {"OBJECTID": 1, "AssessmentNo": "001-000-01", "SiteAddress": "1 Main St"},
            {"OBJECTID": 2, "AssessmentNo": "001-000-02", "SiteAddress": "2 Main St"},
        ],
        2: [
            {"OBJECTID": 3, "AssessmentNo": "001-000-03", "SiteAddress": "3 Main St"},
        ],
        3: [],
    }

    def fetcher_first(last_objectid: int) -> list[dict[str, object]]:
        return list(batches_first_run.get(last_objectid, []))

    summary_first = solis_orange_county_apn_db.sync_apn_database(
        endpoint="https://example.test/FeatureServer/0",
        db_path=db_path,
        checkpoint_path=checkpoint_path,
        summary_path=summary_path,
        batch_size=2,
        timeout=1.0,
        retries=0,
        retry_sleep=0.0,
        max_batches=None,
        reset_checkpoint=False,
        full_refresh=False,
        fields=solis_orange_county_apn_db.DEFAULT_FIELDS,
        fetcher=fetcher_first,
    )

    assert summary_first["total_rows"] == 3
    assert summary_first["total_distinct_apn"] == 3
    assert summary_first["checkpoint_last_objectid"] == 3

    checkpoint_first = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint_first["last_objectid"] == 3
    assert checkpoint_first["rows_written"] == 3

    batches_second_run = {
        3: [
            {"OBJECTID": 4, "AssessmentNo": "001-000-04", "SiteAddress": "4 Main St"},
        ],
        4: [],
    }

    def fetcher_second(last_objectid: int) -> list[dict[str, object]]:
        return list(batches_second_run.get(last_objectid, []))

    summary_second = solis_orange_county_apn_db.sync_apn_database(
        endpoint="https://example.test/FeatureServer/0",
        db_path=db_path,
        checkpoint_path=checkpoint_path,
        summary_path=summary_path,
        batch_size=2,
        timeout=1.0,
        retries=0,
        retry_sleep=0.0,
        max_batches=None,
        reset_checkpoint=False,
        full_refresh=False,
        fields=solis_orange_county_apn_db.DEFAULT_FIELDS,
        fetcher=fetcher_second,
    )

    assert summary_second["total_rows"] == 4
    assert summary_second["total_distinct_apn"] == 4
    assert summary_second["checkpoint_last_objectid"] == 4

    conn = sqlite3.connect(db_path)
    try:
        value = conn.execute(
            "SELECT assessment_no_norm FROM apn_records WHERE objectid = 4"
        ).fetchone()
        assert value == ("00100004",)
    finally:
        conn.close()


def test_sync_apn_database_auto_resets_on_non_overlapping_source_window(tmp_path: Path) -> None:
    db_path = tmp_path / "apn.sqlite3"
    checkpoint_path = tmp_path / "checkpoint.json"
    summary_path = tmp_path / "summary.json"

    batches_old = {
        0: [
            {"OBJECTID": 10, "AssessmentNo": "001-000-10", "SiteAddress": "10 Main St"},
            {"OBJECTID": 11, "AssessmentNo": "001-000-11", "SiteAddress": "11 Main St"},
        ],
        11: [],
    }

    def fetch_old(last_objectid: int) -> list[dict[str, object]]:
        return list(batches_old.get(last_objectid, []))

    solis_orange_county_apn_db.sync_apn_database(
        endpoint="https://example.test/FeatureServer/0",
        db_path=db_path,
        checkpoint_path=checkpoint_path,
        summary_path=summary_path,
        batch_size=2,
        timeout=1.0,
        retries=0,
        retry_sleep=0.0,
        max_batches=None,
        reset_checkpoint=False,
        full_refresh=False,
        fields=solis_orange_county_apn_db.DEFAULT_FIELDS,
        fetcher=fetch_old,
    )

    batches_new = {
        0: [
            {"OBJECTID": 1000, "AssessmentNo": "001-010-00", "SiteAddress": "1000 Main St"},
            {"OBJECTID": 1001, "AssessmentNo": "001-010-01", "SiteAddress": "1001 Main St"},
        ],
        1001: [],
    }

    def fetch_new(last_objectid: int) -> list[dict[str, object]]:
        return list(batches_new.get(last_objectid, []))

    summary = solis_orange_county_apn_db.sync_apn_database(
        endpoint="https://example.test/FeatureServer/0",
        db_path=db_path,
        checkpoint_path=checkpoint_path,
        summary_path=summary_path,
        batch_size=2,
        timeout=1.0,
        retries=0,
        retry_sleep=0.0,
        max_batches=None,
        reset_checkpoint=False,
        full_refresh=False,
        fields=solis_orange_county_apn_db.DEFAULT_FIELDS,
        fetcher=fetch_new,
        source_stats_fetcher=lambda: {"row_count": 2, "min_objectid": 1000, "max_objectid": 1001},
        auto_reset_on_source_rollover=True,
        archive_on_rollover=True,
    )

    assert summary["rollover_detected"] is True
    assert summary["total_rows"] == 2
    assert Path(summary["db_archive_path"]).exists()
    assert Path(summary["checkpoint_archive_path"]).exists()

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT objectid FROM apn_records ORDER BY objectid").fetchall()
        assert rows == [(1000,), (1001,)]
    finally:
        conn.close()


def test_sync_apn_database_prunes_stale_rows_outside_source_window(tmp_path: Path) -> None:
    db_path = tmp_path / "apn.sqlite3"
    checkpoint_path = tmp_path / "checkpoint.json"
    summary_path = tmp_path / "summary.json"

    initial_batches = {
        0: [
            {"OBJECTID": 10, "AssessmentNo": "001-000-10", "SiteAddress": "10 Main St"},
            {"OBJECTID": 11, "AssessmentNo": "001-000-11", "SiteAddress": "11 Main St"},
            {"OBJECTID": 1000, "AssessmentNo": "001-010-00", "SiteAddress": "1000 Main St"},
        ],
        1000: [],
    }

    def fetch_initial(last_objectid: int) -> list[dict[str, object]]:
        return list(initial_batches.get(last_objectid, []))

    solis_orange_county_apn_db.sync_apn_database(
        endpoint="https://example.test/FeatureServer/0",
        db_path=db_path,
        checkpoint_path=checkpoint_path,
        summary_path=summary_path,
        batch_size=3,
        timeout=1.0,
        retries=0,
        retry_sleep=0.0,
        max_batches=None,
        reset_checkpoint=False,
        full_refresh=False,
        fields=solis_orange_county_apn_db.DEFAULT_FIELDS,
        fetcher=fetch_initial,
    )

    summary = solis_orange_county_apn_db.sync_apn_database(
        endpoint="https://example.test/FeatureServer/0",
        db_path=db_path,
        checkpoint_path=checkpoint_path,
        summary_path=summary_path,
        batch_size=3,
        timeout=1.0,
        retries=0,
        retry_sleep=0.0,
        max_batches=None,
        reset_checkpoint=False,
        full_refresh=False,
        fields=solis_orange_county_apn_db.DEFAULT_FIELDS,
        fetcher=lambda _last_objectid: [],
        source_stats_fetcher=lambda: {"row_count": 2, "min_objectid": 1000, "max_objectid": 1001},
        auto_reset_on_source_rollover=True,
        archive_on_rollover=True,
    )

    assert summary["rollover_detected"] is False
    assert summary["pruned_rows_below_source_min"] == 2
    assert summary["total_rows"] == 1

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT objectid FROM apn_records ORDER BY objectid").fetchall()
        assert rows == [(1000,)]
    finally:
        conn.close()
