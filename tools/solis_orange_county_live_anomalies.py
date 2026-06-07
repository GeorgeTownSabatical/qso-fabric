from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(".codex/state/orange_county_apn/apn_orange_county_ca.sqlite3")
DEFAULT_SUMMARY_PATH = Path(".codex/state/orange_county_apn/live_anomaly_summary.json")
DEFAULT_VIEW_NAME = "solis_apn_live_metrics"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _solis_apn_id(apn_norm: str) -> str:
    return f"solis:oc:apn:{apn_norm}"


def _solis_anomaly_id(apn_norm: str, anomaly_type: str) -> str:
    text = f"{apn_norm}|{anomaly_type}".encode("utf-8")
    digest = hashlib.sha256(text).hexdigest()[:24]
    return f"solis:oc:anomaly:live:{digest}"


def _connect(db_path: Path, *, timeout_seconds: float) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=timeout_seconds)
    conn.row_factory = sqlite3.Row
    # Keep lock waits bounded so this can run alongside ingest jobs.
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def _ensure_core_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS solis_apn (
            solis_apn_id TEXT PRIMARY KEY,
            assessment_no TEXT NOT NULL,
            assessment_no_norm TEXT NOT NULL UNIQUE,
            first_event_date TEXT,
            last_event_date TEXT,
            fragment_count INTEGER NOT NULL DEFAULT 0,
            legal_lot_count INTEGER NOT NULL DEFAULT 0,
            has_easement_activity INTEGER NOT NULL DEFAULT 0,
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS solis_apn_anomaly (
            solis_anomaly_id TEXT PRIMARY KEY,
            solis_apn_id TEXT NOT NULL,
            anomaly_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            signal_value REAL,
            details_json TEXT NOT NULL,
            detected_at_utc TEXT NOT NULL
        )
        """
    )


def _ensure_live_view(conn: sqlite3.Connection, *, view_name: str) -> None:
    conn.execute(f"DROP VIEW IF EXISTS {view_name}")
    conn.execute(
        f"""
        CREATE VIEW {view_name} AS
        WITH
        dup AS (
            SELECT
                assessment_no_norm AS apn_norm,
                MIN(assessment_no) AS assessment_no,
                COUNT(*) AS duplicate_row_count,
                COUNT(DISTINCT COALESCE(doc_num, '')) AS doc_variants,
                COUNT(DISTINCT COALESCE(map_num, '')) AS map_variants,
                COUNT(DISTINCT COALESCE(legal_lot_id, '')) AS legal_lot_variants,
                COUNT(DISTINCT COALESCE(site_address, '')) AS address_variants,
                COUNT(DISTINCT COALESCE(CAST(assd_amt AS TEXT), '')) AS assd_variants,
                COUNT(DISTINCT fetched_at_utc) AS fetch_versions
            FROM apn_records
            WHERE assessment_no_norm <> ''
            GROUP BY assessment_no_norm
            HAVING COUNT(*) > 1
        ),
        frag_issue AS (
            SELECT
                apn_norm,
                MIN(apn) AS fragment_apn,
                COUNT(*) AS fragment_count,
                SUM(CASE WHEN event_date = '1900-01-01' THEN 1 ELSE 0 END) AS sentinel_1900_count,
                SUM(CASE WHEN event_date IS NULL OR TRIM(event_date) = '' THEN 1 ELSE 0 END) AS missing_event_date_count
            FROM solis_source_fragments
            WHERE apn_norm <> ''
            GROUP BY apn_norm
            HAVING sentinel_1900_count > 0 OR missing_event_date_count > 0
        ),
        unlinked AS (
            SELECT
                f.apn_norm,
                COUNT(*) AS unlinked_fragment_count
            FROM solis_source_fragments AS f
            LEFT JOIN apn_records AS r
                ON r.assessment_no_norm = f.apn_norm
            WHERE f.apn_norm <> '' AND r.assessment_no_norm IS NULL
            GROUP BY f.apn_norm
        ),
        base AS (
            SELECT apn_norm FROM dup
            UNION
            SELECT apn_norm FROM frag_issue
            UNION
            SELECT apn_norm FROM unlinked
        ),
        apn_name AS (
            SELECT assessment_no_norm AS apn_norm, MIN(assessment_no) AS assessment_no
            FROM apn_records
            WHERE assessment_no_norm <> ''
            GROUP BY assessment_no_norm
        ),
        frag_name AS (
            SELECT apn_norm, MIN(apn) AS apn
            FROM solis_source_fragments
            WHERE apn_norm <> ''
            GROUP BY apn_norm
        )
        SELECT
            b.apn_norm AS assessment_no_norm,
            COALESCE(an.assessment_no, fn.apn, b.apn_norm) AS assessment_no,
            COALESCE(d.duplicate_row_count, 0) AS duplicate_row_count,
            COALESCE(d.doc_variants, 0) AS doc_variants,
            COALESCE(d.map_variants, 0) AS map_variants,
            COALESCE(d.legal_lot_variants, 0) AS legal_lot_variants,
            COALESCE(d.address_variants, 0) AS address_variants,
            COALESCE(d.assd_variants, 0) AS assd_variants,
            COALESCE(d.fetch_versions, 0) AS fetch_versions,
            COALESCE(fi.fragment_count, 0) AS fragment_count,
            COALESCE(fi.sentinel_1900_count, 0) AS sentinel_1900_count,
            COALESCE(fi.missing_event_date_count, 0) AS missing_event_date_count,
            COALESCE(u.unlinked_fragment_count, 0) AS unlinked_fragment_count
        FROM base AS b
        LEFT JOIN dup AS d ON d.apn_norm = b.apn_norm
        LEFT JOIN frag_issue AS fi ON fi.apn_norm = b.apn_norm
        LEFT JOIN unlinked AS u ON u.apn_norm = b.apn_norm
        LEFT JOIN apn_name AS an ON an.apn_norm = b.apn_norm
        LEFT JOIN frag_name AS fn ON fn.apn_norm = b.apn_norm
        """
    )


def _severity_doc_map(row_count: int, doc_variants: int, map_variants: int) -> str:
    if row_count >= 30 or (doc_variants + map_variants) >= 12:
        return "high"
    if row_count >= 10 or (doc_variants + map_variants) >= 5:
        return "medium"
    return "low"


def _severity_legal_lot(legal_lot_variants: int, row_count: int) -> str:
    if legal_lot_variants >= 20 or row_count >= 30:
        return "high"
    if legal_lot_variants >= 8:
        return "medium"
    return "low"


def _build_live_anomalies(conn: sqlite3.Connection, *, view_name: str) -> tuple[list[tuple[Any, ...]], dict[str, int]]:
    rows = conn.execute(f"SELECT * FROM {view_name}").fetchall()
    now = _utc_now()
    anomalies: list[tuple[Any, ...]] = []
    type_counts: Counter[str] = Counter()

    for row in rows:
        apn_norm = str(row["assessment_no_norm"])
        apn = str(row["assessment_no"] or apn_norm)
        apn_id = _solis_apn_id(apn_norm)

        duplicate_row_count = int(row["duplicate_row_count"] or 0)
        doc_variants = int(row["doc_variants"] or 0)
        map_variants = int(row["map_variants"] or 0)
        legal_lot_variants = int(row["legal_lot_variants"] or 0)
        address_variants = int(row["address_variants"] or 0)
        assd_variants = int(row["assd_variants"] or 0)
        fetch_versions = int(row["fetch_versions"] or 0)
        fragment_count = int(row["fragment_count"] or 0)
        sentinel_1900 = int(row["sentinel_1900_count"] or 0)
        missing_event = int(row["missing_event_date_count"] or 0)
        unlinked = int(row["unlinked_fragment_count"] or 0)

        if duplicate_row_count >= 2 and (doc_variants > 1 or map_variants > 1):
            anomaly_type = "live_doc_map_churn"
            details = {
                "assessment_no": apn,
                "duplicate_row_count": duplicate_row_count,
                "doc_variants": doc_variants,
                "map_variants": map_variants,
                "fetch_versions": fetch_versions,
            }
            anomalies.append(
                (
                    _solis_anomaly_id(apn_norm, anomaly_type),
                    apn_id,
                    anomaly_type,
                    _severity_doc_map(duplicate_row_count, doc_variants, map_variants),
                    float(doc_variants + map_variants),
                    json.dumps(details, sort_keys=True),
                    now,
                )
            )
            type_counts[anomaly_type] += 1

        if (
            duplicate_row_count >= 2
            and legal_lot_variants > 1
            and doc_variants == 1
            and map_variants == 1
            and address_variants == 1
            and assd_variants <= 1
        ):
            anomaly_type = "live_legal_lot_churn"
            details = {
                "assessment_no": apn,
                "duplicate_row_count": duplicate_row_count,
                "legal_lot_variants": legal_lot_variants,
                "fetch_versions": fetch_versions,
            }
            anomalies.append(
                (
                    _solis_anomaly_id(apn_norm, anomaly_type),
                    apn_id,
                    anomaly_type,
                    _severity_legal_lot(legal_lot_variants, duplicate_row_count),
                    float(legal_lot_variants),
                    json.dumps(details, sort_keys=True),
                    now,
                )
            )
            type_counts[anomaly_type] += 1

        if duplicate_row_count >= 20:
            anomaly_type = "live_duplicate_density"
            details = {
                "assessment_no": apn,
                "duplicate_row_count": duplicate_row_count,
                "fetch_versions": fetch_versions,
            }
            anomalies.append(
                (
                    _solis_anomaly_id(apn_norm, anomaly_type),
                    apn_id,
                    anomaly_type,
                    "high",
                    float(duplicate_row_count),
                    json.dumps(details, sort_keys=True),
                    now,
                )
            )
            type_counts[anomaly_type] += 1

        if sentinel_1900 > 0:
            anomaly_type = "live_sentinel_event_date_1900"
            details = {
                "assessment_no": apn,
                "fragment_count": fragment_count,
                "sentinel_1900_count": sentinel_1900,
            }
            severity = "high" if sentinel_1900 >= 10 else "medium" if sentinel_1900 >= 3 else "low"
            anomalies.append(
                (
                    _solis_anomaly_id(apn_norm, anomaly_type),
                    apn_id,
                    anomaly_type,
                    severity,
                    float(sentinel_1900),
                    json.dumps(details, sort_keys=True),
                    now,
                )
            )
            type_counts[anomaly_type] += 1

        if missing_event > 0:
            anomaly_type = "live_missing_event_date"
            details = {
                "assessment_no": apn,
                "fragment_count": fragment_count,
                "missing_event_date_count": missing_event,
            }
            severity = "high" if missing_event >= 10 else "medium" if missing_event >= 3 else "low"
            anomalies.append(
                (
                    _solis_anomaly_id(apn_norm, anomaly_type),
                    apn_id,
                    anomaly_type,
                    severity,
                    float(missing_event),
                    json.dumps(details, sort_keys=True),
                    now,
                )
            )
            type_counts[anomaly_type] += 1

        if unlinked > 0:
            anomaly_type = "live_unlinked_fragment_apn"
            details = {
                "assessment_no": apn,
                "unlinked_fragment_count": unlinked,
            }
            severity = "high" if unlinked >= 20 else "medium" if unlinked >= 5 else "low"
            anomalies.append(
                (
                    _solis_anomaly_id(apn_norm, anomaly_type),
                    apn_id,
                    anomaly_type,
                    severity,
                    float(unlinked),
                    json.dumps(details, sort_keys=True),
                    now,
                )
            )
            type_counts[anomaly_type] += 1

    return anomalies, dict(type_counts)


def _upsert_live_anomalies(
    conn: sqlite3.Connection,
    *,
    anomalies: list[tuple[Any, ...]],
    view_name: str,
) -> None:
    if not anomalies:
        with conn:
            conn.execute("DELETE FROM solis_apn_anomaly WHERE anomaly_type LIKE 'live_%'")
        return

    now = _utc_now()

    with conn:
        # Ensure impacted APNs exist.
        rows = conn.execute(
            f"SELECT assessment_no_norm, assessment_no FROM {view_name}"
        ).fetchall()
        conn.executemany(
            """
            INSERT INTO solis_apn (
                solis_apn_id,
                assessment_no,
                assessment_no_norm,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(assessment_no_norm) DO UPDATE SET
                assessment_no=excluded.assessment_no,
                updated_at_utc=excluded.updated_at_utc
            """,
            [
                (
                    _solis_apn_id(str(r["assessment_no_norm"])),
                    str(r["assessment_no"] or r["assessment_no_norm"]),
                    str(r["assessment_no_norm"]),
                    now,
                    now,
                )
                for r in rows
            ],
        )

        conn.execute("DELETE FROM solis_apn_anomaly WHERE anomaly_type LIKE 'live_%'")
        conn.executemany(
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
            ON CONFLICT(solis_anomaly_id) DO UPDATE SET
                severity=excluded.severity,
                signal_value=excluded.signal_value,
                details_json=excluded.details_json,
                detected_at_utc=excluded.detected_at_utc
            """,
            anomalies,
        )


def refresh_live_anomalies(
    db_path: Path,
    *,
    summary_path: Path | None,
    view_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path, timeout_seconds=timeout_seconds)
    try:
        _ensure_core_tables(conn)
        _ensure_live_view(conn, view_name=view_name)
        anomalies, type_counts = _build_live_anomalies(conn, view_name=view_name)
        _upsert_live_anomalies(conn, anomalies=anomalies, view_name=view_name)

        total_live = int(
            conn.execute(
                "SELECT COUNT(*) FROM solis_apn_anomaly WHERE anomaly_type LIKE 'live_%'"
            ).fetchone()[0]
        )
        summary = {
            "generated_at_utc": _utc_now(),
            "db_path": str(db_path),
            "view_name": view_name,
            "live_anomaly_count": total_live,
            "live_anomaly_type_counts": type_counts,
            "status": "ok",
        }
    except sqlite3.OperationalError as exc:
        summary = {
            "generated_at_utc": _utc_now(),
            "db_path": str(db_path),
            "view_name": view_name,
            "live_anomaly_count": None,
            "live_anomaly_type_counts": {},
            "status": "locked",
            "error": str(exc),
        }
    finally:
        conn.close()

    if summary_path is not None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Continuously refresh live APN anomalies while Orange County ingest/build runs. "
            "Creates SQL view metrics and writes live_* anomalies into solis_apn_anomaly."
        )
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite APN database path.")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY_PATH, help="Summary JSON output path.")
    parser.add_argument("--view-name", default=DEFAULT_VIEW_NAME, help="Live metrics SQL view name.")
    parser.add_argument("--watch", action="store_true", help="Continuously refresh anomalies.")
    parser.add_argument("--interval", type=float, default=20.0, help="Watch interval in seconds.")
    parser.add_argument("--max-cycles", type=int, default=None, help="Optional max cycles in watch mode.")
    parser.add_argument("--timeout-seconds", type=float, default=5.0, help="SQLite connection timeout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    cycles = 0

    while True:
        summary = refresh_live_anomalies(
            db_path=args.db,
            summary_path=args.summary,
            view_name=args.view_name,
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(summary, sort_keys=True))
        cycles += 1

        if not args.watch:
            return 0 if summary.get("status") == "ok" else 1
        if args.max_cycles is not None and cycles >= args.max_cycles:
            return 0
        time.sleep(max(1.0, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
