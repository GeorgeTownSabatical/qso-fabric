from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = Path(".codex/state/orange_county_apn/apn_orange_county_ca.sqlite3")
DEFAULT_OUTPUT_ROOT = Path(".codex/state/orange_county_apn/kaggle_exports")


def _dataset_queries() -> dict[str, str]:
    return {
        "oc_apn_core": """
            WITH
            state_counts AS (
                SELECT solis_apn_id, COUNT(*) AS state_count
                FROM solis_apn_state
                GROUP BY solis_apn_id
            ),
            transition_counts AS (
                SELECT solis_apn_id, COUNT(*) AS transition_count
                FROM solis_apn_transition
                GROUP BY solis_apn_id
            ),
            anomaly_counts AS (
                SELECT solis_apn_id, COUNT(*) AS anomaly_count
                FROM solis_apn_anomaly
                GROUP BY solis_apn_id
            )
            SELECT
                sa.solis_apn_id,
                sa.assessment_no,
                sa.assessment_no_norm,
                latest.objectid AS latest_objectid,
                latest.legal_lot_id,
                latest.doc_num,
                latest.map_num,
                latest.site_address,
                latest.site_city_state,
                latest.site_zip5,
                latest.assd_amt,
                latest.land_val,
                latest.improved_val,
                latest.gplu_code,
                latest.gplu_desc,
                latest.zclass,
                sa.first_event_date,
                sa.last_event_date,
                sa.fragment_count,
                sa.legal_lot_count,
                sa.has_easement_activity,
                COALESCE(st.state_count, COALESCE(sc.state_count, 0)) AS state_count,
                COALESCE(tr.transition_count, COALESCE(sc.transition_count, 0)) AS transition_count,
                COALESCE(an.anomaly_count, COALESCE(sc.anomaly_count, 0)) AS anomaly_count,
                sc.built_at_utc
            FROM solis_apn AS sa
            LEFT JOIN apn_records AS latest
                ON latest.assessment_no_norm = sa.assessment_no_norm
               AND latest.objectid = (
                   SELECT MAX(r2.objectid)
                   FROM apn_records AS r2
                   WHERE r2.assessment_no_norm = sa.assessment_no_norm
               )
            LEFT JOIN solis_apn_scope AS sc
                ON sc.solis_apn_id = sa.solis_apn_id
            LEFT JOIN state_counts AS st
                ON st.solis_apn_id = sa.solis_apn_id
            LEFT JOIN transition_counts AS tr
                ON tr.solis_apn_id = sa.solis_apn_id
            LEFT JOIN anomaly_counts AS an
                ON an.solis_apn_id = sa.solis_apn_id
            ORDER BY sa.assessment_no_norm
        """,
        "oc_parcel_states": """
            SELECT
                st.solis_state_id,
                st.solis_apn_id,
                sa.assessment_no,
                sa.assessment_no_norm,
                st.state_sequence,
                st.event_date,
                st.source_id,
                st.source_objectid,
                st.doc_num,
                st.map_num,
                st.legal_lot_id,
                st.solis_fragment_id,
                st.state_hash
            FROM solis_apn_state AS st
            JOIN solis_apn AS sa
                ON sa.solis_apn_id = st.solis_apn_id
            ORDER BY sa.assessment_no_norm, st.state_sequence
        """,
        "oc_parcel_transitions": """
            SELECT
                tr.solis_transition_id,
                tr.solis_apn_id,
                sa.assessment_no,
                sa.assessment_no_norm,
                tr.from_state_id,
                tr.to_state_id,
                tr.transition_days,
                tr.trigger_doc_num,
                tr.trigger_map_num
            FROM solis_apn_transition AS tr
            JOIN solis_apn AS sa
                ON sa.solis_apn_id = tr.solis_apn_id
            ORDER BY sa.assessment_no_norm, tr.from_state_id, tr.to_state_id
        """,
        "oc_parcel_anomalies": """
            SELECT
                an.solis_anomaly_id,
                an.solis_apn_id,
                sa.assessment_no,
                sa.assessment_no_norm,
                an.anomaly_type,
                an.severity,
                an.signal_value,
                an.details_json,
                an.detected_at_utc
            FROM solis_apn_anomaly AS an
            LEFT JOIN solis_apn AS sa
                ON sa.solis_apn_id = an.solis_apn_id
            ORDER BY sa.assessment_no_norm, an.anomaly_type, an.solis_anomaly_id
        """,
        "oc_risk_snapshot": """
            WITH
            latest_record AS (
                SELECT
                    r.assessment_no_norm,
                    r.objectid,
                    r.assessment_no,
                    r.legal_lot_id,
                    r.doc_num,
                    r.map_num,
                    r.site_address,
                    r.site_city_state,
                    r.site_zip5,
                    r.assd_amt,
                    r.land_val,
                    r.improved_val,
                    r.gplu_code,
                    r.gplu_desc,
                    r.zclass
                FROM apn_records AS r
                INNER JOIN (
                    SELECT assessment_no_norm, MAX(objectid) AS objectid
                    FROM apn_records
                    WHERE assessment_no_norm <> ''
                    GROUP BY assessment_no_norm
                ) AS newest
                    ON newest.assessment_no_norm = r.assessment_no_norm
                   AND newest.objectid = r.objectid
            ),
            duplicate_stats AS (
                SELECT
                    assessment_no_norm,
                    COUNT(*) AS duplicate_row_count
                FROM apn_records
                WHERE assessment_no_norm <> ''
                GROUP BY assessment_no_norm
            ),
            anomaly_features AS (
                SELECT
                    solis_apn_id,
                    COUNT(*) AS anomaly_count,
                    SUM(
                        CASE severity
                            WHEN 'high' THEN 1.0
                            WHEN 'medium' THEN 0.5
                            ELSE 0.2
                        END
                    ) AS weighted_anomaly_signal,
                    SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) AS high_severity_anomaly_count
                FROM solis_apn_anomaly
                GROUP BY solis_apn_id
            ),
            state_counts AS (
                SELECT solis_apn_id, COUNT(*) AS state_count
                FROM solis_apn_state
                GROUP BY solis_apn_id
            ),
            transition_counts AS (
                SELECT solis_apn_id, COUNT(*) AS transition_count
                FROM solis_apn_transition
                GROUP BY solis_apn_id
            ),
            state_summary AS (
                SELECT
                    solis_apn_id,
                    COUNT(*) AS live_state_count,
                    MIN(event_date) AS first_state_date,
                    MAX(event_date) AS last_state_date,
                    COUNT(DISTINCT source_id) AS distinct_source_count,
                    COUNT(
                        DISTINCT CASE
                            WHEN doc_num IS NOT NULL AND TRIM(doc_num) <> '' THEN doc_num
                        END
                    ) AS distinct_doc_count
                FROM solis_apn_state
                GROUP BY solis_apn_id
            ),
            state_recent AS (
                SELECT
                    st.solis_apn_id,
                    SUM(
                        CASE
                            WHEN ss.last_state_date IS NOT NULL
                                 AND st.event_date >= DATE(ss.last_state_date, '-365 day')
                            THEN 1
                            ELSE 0
                        END
                    ) AS recent_event_count_365d
                FROM solis_apn_state AS st
                JOIN state_summary AS ss
                    ON ss.solis_apn_id = st.solis_apn_id
                GROUP BY st.solis_apn_id
            ),
            state_same_day AS (
                SELECT
                    solis_apn_id,
                    SUM(day_count - 1) AS same_day_repeat_count
                FROM (
                    SELECT
                        solis_apn_id,
                        event_date,
                        COUNT(*) AS day_count
                    FROM solis_apn_state
                    WHERE event_date IS NOT NULL
                    GROUP BY solis_apn_id, event_date
                    HAVING COUNT(*) > 1
                )
                GROUP BY solis_apn_id
            ),
            transition_features AS (
                SELECT
                    solis_apn_id,
                    COUNT(*) AS live_transition_count,
                    SUM(CASE WHEN transition_days IS NOT NULL AND transition_days <= 90 THEN 1 ELSE 0 END) AS short_transition_count_90d,
                    SUM(CASE WHEN transition_days = 0 THEN 1 ELSE 0 END) AS zero_day_transition_count,
                    SUM(CASE WHEN transition_days < 0 THEN 1 ELSE 0 END) AS negative_transition_count,
                    AVG(CASE WHEN transition_days IS NOT NULL THEN transition_days END) AS avg_transition_days
                FROM solis_apn_transition
                GROUP BY solis_apn_id
            ),
            feature_rows AS (
                SELECT
                    DATE('now') AS snapshot_date,
                    sa.solis_apn_id,
                    sa.assessment_no,
                    sa.assessment_no_norm,
                    COALESCE(lr.site_city_state, '') AS site_city_state,
                    COALESCE(lr.site_zip5, '') AS site_zip5,
                    COALESCE(lr.gplu_code, '') AS gplu_code,
                    COALESCE(lr.gplu_desc, '') AS gplu_desc,
                    COALESCE(lr.zclass, '') AS zclass,
                    COALESCE(ss.live_state_count, COALESCE(st.state_count, COALESCE(sc.state_count, 0))) AS state_count,
                    COALESCE(tf.live_transition_count, COALESCE(tr.transition_count, COALESCE(sc.transition_count, 0))) AS transition_count,
                    COALESCE(af.anomaly_count, COALESCE(sc.anomaly_count, 0)) AS anomaly_count,
                    COALESCE(af.high_severity_anomaly_count, 0) AS high_severity_anomaly_count,
                    COALESCE(af.weighted_anomaly_signal, 0.0) AS weighted_anomaly_signal,
                    COALESCE(sa.fragment_count, 0) AS fragment_count,
                    COALESCE(sa.legal_lot_count, 0) AS legal_lot_count,
                    COALESCE(sa.has_easement_activity, 0) AS has_easement_activity,
                    COALESCE(ds.duplicate_row_count, 0) AS duplicate_row_count,
                    COALESCE(ss.distinct_source_count, 0) AS distinct_source_count,
                    COALESCE(ss.distinct_doc_count, 0) AS distinct_doc_count,
                    COALESCE(CAST(julianday(ss.last_state_date) - julianday(ss.first_state_date) AS INTEGER), 0) AS state_span_days,
                    COALESCE(sr.recent_event_count_365d, 0) AS recent_event_count_365d,
                    COALESCE(sd.same_day_repeat_count, 0) AS same_day_repeat_count,
                    COALESCE(tf.short_transition_count_90d, 0) AS short_transition_count_90d,
                    COALESCE(tf.zero_day_transition_count, 0) AS zero_day_transition_count,
                    COALESCE(tf.negative_transition_count, 0) AS negative_transition_count,
                    COALESCE(tf.avg_transition_days, 0.0) AS avg_transition_days,
                    COALESCE(lr.assd_amt, 0.0) AS assd_amt,
                    COALESCE(lr.land_val, 0.0) AS land_val,
                    COALESCE(lr.improved_val, 0.0) AS improved_val,
                    MIN(0.20, COALESCE(af.weighted_anomaly_signal, 0.0) / 10.0) AS anomaly_component,
                    MIN(0.05, COALESCE(sa.fragment_count, 0) / 200.0) AS fragment_component,
                    MIN(0.10, COALESCE(ss.live_state_count, COALESCE(st.state_count, COALESCE(sc.state_count, 0))) / 40.0) AS state_component,
                    CASE
                        WHEN COALESCE(ss.live_state_count, COALESCE(st.state_count, COALESCE(sc.state_count, 0))) >= 8
                             AND COALESCE(CAST(julianday(ss.last_state_date) - julianday(ss.first_state_date) AS INTEGER), 0) <= 365
                        THEN 0.15
                        WHEN COALESCE(ss.live_state_count, COALESCE(st.state_count, COALESCE(sc.state_count, 0))) >= 4
                             AND COALESCE(CAST(julianday(ss.last_state_date) - julianday(ss.first_state_date) AS INTEGER), 0) <= 90
                        THEN 0.12
                        WHEN COALESCE(ss.live_state_count, COALESCE(st.state_count, COALESCE(sc.state_count, 0))) >= 12
                        THEN 0.10
                        ELSE MIN(
                            0.08,
                            COALESCE(ss.live_state_count, COALESCE(st.state_count, COALESCE(sc.state_count, 0))) / 60.0
                        )
                    END AS history_density_component,
                    MIN(
                        0.20,
                        MIN(0.12, COALESCE(sr.recent_event_count_365d, 0) / 25.0)
                        + MIN(0.08, COALESCE(sd.same_day_repeat_count, 0) / 8.0)
                    ) AS velocity_component,
                    MIN(
                        0.15,
                        MIN(0.08, COALESCE(tf.short_transition_count_90d, 0) / 12.0)
                        + MIN(0.03, COALESCE(tf.zero_day_transition_count, 0) / 2.0)
                        + CASE WHEN COALESCE(tf.negative_transition_count, 0) > 0 THEN 0.04 ELSE 0.0 END
                    ) AS transition_component,
                    MIN(
                        0.10,
                        MIN(0.06, COALESCE(ss.distinct_source_count, 0) / 8.0)
                        + MIN(0.02, COALESCE(ss.distinct_doc_count, 0) / 15.0)
                        + MIN(0.02, COALESCE(af.high_severity_anomaly_count, 0) / 4.0)
                    ) AS source_component,
                    CASE WHEN COALESCE(sa.has_easement_activity, 0) > 0 THEN 0.04 ELSE 0.0 END AS easement_component,
                    CASE
                        WHEN COALESCE(ds.duplicate_row_count, 0) <= 1 THEN 0.0
                        ELSE MIN(0.08, (COALESCE(ds.duplicate_row_count, 0) - 1) / 15.0)
                    END AS duplicate_component,
                    CASE
                        WHEN COALESCE(lr.assd_amt, 0.0) <= 0.0 THEN 0.0
                        ELSE MIN(
                            0.08,
                            ABS((COALESCE(lr.land_val, 0.0) + COALESCE(lr.improved_val, 0.0)) - COALESCE(lr.assd_amt, 0.0))
                            / NULLIF(COALESCE(lr.assd_amt, 0.0), 0.0)
                        )
                    END AS valuation_component
                FROM solis_apn AS sa
                LEFT JOIN latest_record AS lr
                    ON lr.assessment_no_norm = sa.assessment_no_norm
                LEFT JOIN duplicate_stats AS ds
                    ON ds.assessment_no_norm = sa.assessment_no_norm
                LEFT JOIN solis_apn_scope AS sc
                    ON sc.solis_apn_id = sa.solis_apn_id
                LEFT JOIN anomaly_features AS af
                    ON af.solis_apn_id = sa.solis_apn_id
                LEFT JOIN state_counts AS st
                    ON st.solis_apn_id = sa.solis_apn_id
                LEFT JOIN transition_counts AS tr
                    ON tr.solis_apn_id = sa.solis_apn_id
                LEFT JOIN state_summary AS ss
                    ON ss.solis_apn_id = sa.solis_apn_id
                LEFT JOIN state_recent AS sr
                    ON sr.solis_apn_id = sa.solis_apn_id
                LEFT JOIN state_same_day AS sd
                    ON sd.solis_apn_id = sa.solis_apn_id
                LEFT JOIN transition_features AS tf
                    ON tf.solis_apn_id = sa.solis_apn_id
            ),
            scored AS (
                SELECT
                    *,
                    MIN(
                        1.0,
                        anomaly_component
                        + fragment_component
                        + state_component
                        + history_density_component
                        + velocity_component
                        + transition_component
                        + source_component
                        + easement_component
                        + duplicate_component
                        + valuation_component
                    ) AS risk_score
                FROM feature_rows
            )
            SELECT
                snapshot_date,
                solis_apn_id,
                assessment_no,
                assessment_no_norm,
                site_city_state,
                site_zip5,
                gplu_code,
                gplu_desc,
                zclass,
                state_count,
                transition_count,
                anomaly_count,
                high_severity_anomaly_count,
                weighted_anomaly_signal,
                fragment_count,
                legal_lot_count,
                has_easement_activity,
                duplicate_row_count,
                distinct_source_count,
                distinct_doc_count,
                state_span_days,
                recent_event_count_365d,
                same_day_repeat_count,
                short_transition_count_90d,
                zero_day_transition_count,
                negative_transition_count,
                avg_transition_days,
                assd_amt,
                land_val,
                improved_val,
                anomaly_component,
                fragment_component,
                state_component,
                history_density_component,
                velocity_component,
                transition_component,
                source_component,
                easement_component,
                duplicate_component,
                valuation_component,
                risk_score,
                CASE
                    WHEN risk_score < 0.30 THEN 'low'
                    WHEN risk_score < 0.50 THEN 'elevated'
                    WHEN risk_score < 0.70 THEN 'coordinated'
                    WHEN risk_score < 0.85 THEN 'structured'
                    ELSE 'critical'
                END AS risk_bucket
            FROM scored
            ORDER BY risk_score DESC, assessment_no_norm
        """,
    }


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_release_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _sha256_bytes(data: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(data)
    return digest.hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _json_dump(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def _require_schema(conn: sqlite3.Connection) -> None:
    required = [
        "apn_records",
        "solis_apn",
        "solis_apn_state",
        "solis_apn_transition",
        "solis_apn_anomaly",
        "solis_apn_scope",
    ]
    missing = [name for name in required if not _table_exists(conn, name)]
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise RuntimeError(
            f"missing required Solis tables: {missing_list}; run solis-orange-county-apn-db and solis-orange-county-scope first"
        )


def _validate_consistency(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "solis_apn_count": int(conn.execute("SELECT COUNT(*) FROM solis_apn").fetchone()[0]),
        "solis_apn_state_count": int(conn.execute("SELECT COUNT(*) FROM solis_apn_state").fetchone()[0]),
        "solis_apn_transition_count": int(conn.execute("SELECT COUNT(*) FROM solis_apn_transition").fetchone()[0]),
        "solis_apn_anomaly_count": int(conn.execute("SELECT COUNT(*) FROM solis_apn_anomaly").fetchone()[0]),
        "solis_apn_scope_count": int(conn.execute("SELECT COUNT(*) FROM solis_apn_scope").fetchone()[0]),
    }


def _query_rows(conn: sqlite3.Connection, query: str) -> tuple[list[str], list[dict[str, Any]]]:
    cursor = conn.execute(query)
    columns = [str(item[0]) for item in cursor.description or ()]
    rows = [dict(row) for row in cursor.fetchall()]
    return columns, rows


def _write_jsonl(columns: list[str], rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            ordered = {key: row.get(key) for key in columns}
            handle.write(_canonical_json(ordered) + "\n")


def _write_parquet(columns: list[str], rows: list[dict[str, Any]], path: Path) -> None:
    try:
        import polars as pl
    except ImportError:
        pl = None
    if pl is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {column: [row.get(column) for row in rows] for column in columns}
        frame = pl.DataFrame(payload)
        frame.write_parquet(path, compression="zstd")
        return

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "parquet export requires `polars` or `pyarrow`; install with `pip install -e '.[kaggle]'`"
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {column: [row.get(column) for row in rows] for column in columns}
    table = pa.table(payload)
    pq.write_table(table, path, compression="zstd")


def _write_dataset(
    *,
    columns: list[str],
    rows: list[dict[str, Any]],
    path: Path,
    format_name: str,
) -> None:
    if format_name == "parquet":
        _write_parquet(columns, rows, path)
        return
    if format_name == "jsonl":
        _write_jsonl(columns, rows, path)
        return
    raise ValueError(f"unsupported format: {format_name}")


def _write_release_readme(
    *,
    release_dir: Path,
    release_id: str,
    manifest: dict[str, Any],
) -> dict[str, str]:
    lines = [
        f"# Solis Orange County Export {release_id}",
        "",
        "This directory contains a deterministic Orange County APN export derived from the local Solis ledger.",
        "",
        "## Datasets",
    ]
    for dataset in manifest["datasets"]:
        lines.append(
            f"- `{dataset['dataset_name']}` rows={dataset['row_count']} sha256={dataset['sha256']}"
        )
    readme_path = release_dir / "README.md"
    readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "path": _display_path(readme_path),
        "sha256": _sha256_file(readme_path),
    }


def _write_kaggle_metadata(
    *,
    release_dir: Path,
    release_id: str,
    kaggle_id: str,
    title: str,
) -> dict[str, Any]:
    metadata = {
        "title": title,
        "id": kaggle_id,
        "licenses": [{"name": "CC0-1.0"}],
        "keywords": ["orange-county", "apn", "gis", "solis", "property-intelligence"],
        "subtitle": f"Versioned Solis Orange County export {release_id}",
    }
    metadata_path = release_dir / "dataset-metadata.json"
    metadata_path.write_text(_json_dump(metadata), encoding="utf-8")
    return {
        "path": _display_path(metadata_path),
        "sha256": _sha256_file(metadata_path),
        "kaggle_id": kaggle_id,
        "title": title,
    }


def _run_kaggle_publish(
    *,
    release_dir: Path,
    create: bool,
    message: str,
) -> dict[str, Any]:
    cmd = ["kaggle", "datasets", "create" if create else "version", "-p", str(release_dir)]
    if not create:
        cmd.extend(["-m", message])
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def export_release(
    *,
    db_path: Path,
    output_root: Path,
    release_id: str,
    format_name: str,
    kaggle_id: str,
    kaggle_title: str,
    publish_kaggle: bool,
    create_kaggle: bool,
    kaggle_message: str,
) -> dict[str, Any]:
    if not db_path.exists():
        raise RuntimeError(f"missing sqlite database: {db_path}")

    release_dir = output_root / release_id
    if release_dir.exists():
        raise RuntimeError(f"release directory already exists: {release_dir}")
    release_dir.mkdir(parents=True, exist_ok=False)

    conn = _connect(db_path)
    try:
        _require_schema(conn)
        consistency = _validate_consistency(conn)
        dataset_summaries: list[dict[str, Any]] = []

        for dataset_name, query in _dataset_queries().items():
            columns, rows = _query_rows(conn, query)
            extension = "parquet" if format_name == "parquet" else "jsonl"
            dataset_path = release_dir / f"{dataset_name}.{extension}"
            _write_dataset(columns=columns, rows=rows, path=dataset_path, format_name=format_name)
            dataset_summaries.append(
                {
                    "dataset_name": dataset_name,
                    "columns": columns,
                    "row_count": len(rows),
                    "path": _display_path(dataset_path),
                    "sha256": _sha256_file(dataset_path),
                }
            )
    finally:
        conn.close()

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "created_at": _utc_now(),
        "release_id": release_id,
        "format": format_name,
        "consistency": consistency,
        "source_db": {
            "path": str(db_path),
            "sha256": _sha256_file(db_path),
        },
        "datasets": dataset_summaries,
        "release_hash": _sha256_bytes(_canonical_json(dataset_summaries).encode("utf-8")),
        "release_readme": None,
        "kaggle_metadata": None,
        "kaggle_publish": None,
    }
    manifest["release_readme"] = _write_release_readme(
        release_dir=release_dir,
        release_id=release_id,
        manifest=manifest,
    )

    if kaggle_id.strip():
        title = kaggle_title.strip() or f"Solis Orange County APN Export {release_id}"
        manifest["kaggle_metadata"] = _write_kaggle_metadata(
            release_dir=release_dir,
            release_id=release_id,
            kaggle_id=kaggle_id.strip(),
            title=title,
        )
        if publish_kaggle:
            manifest["kaggle_publish"] = _run_kaggle_publish(
                release_dir=release_dir,
                create=create_kaggle,
                message=kaggle_message or f"Release {release_id}",
            )

    manifest_path = release_dir / "manifest.json"
    manifest_path.write_text(_json_dump(manifest), encoding="utf-8")
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solis-orange-county-kaggle-export",
        description="Export Orange County Solis APN state into versioned Kaggle-ready datasets.",
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database produced by the Orange County APN + scope pipelines.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory for immutable export releases.",
    )
    parser.add_argument(
        "--release-id",
        default="",
        help="Optional release identifier. Defaults to UTC timestamp.",
    )
    parser.add_argument(
        "--format",
        choices=("parquet", "jsonl"),
        default="parquet",
        help="Dataset format. Use parquet for Kaggle and jsonl for lightweight local inspection.",
    )
    parser.add_argument(
        "--kaggle-id",
        default="",
        help="Optional Kaggle dataset id in owner/dataset-name form. Generates dataset-metadata.json when provided.",
    )
    parser.add_argument(
        "--kaggle-title",
        default="",
        help="Optional Kaggle dataset title. Defaults to a title derived from the release id.",
    )
    parser.add_argument(
        "--publish-kaggle",
        action="store_true",
        help="Run `kaggle datasets version` for the release after export.",
    )
    parser.add_argument(
        "--create-kaggle",
        action="store_true",
        help="Use `kaggle datasets create` instead of `version` when publishing.",
    )
    parser.add_argument(
        "--kaggle-message",
        default="",
        help="Optional version message used when publishing to Kaggle.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    release_id = args.release_id.strip() or _default_release_id()
    manifest = export_release(
        db_path=(ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db),
        output_root=(ROOT / args.output_root).resolve()
        if not Path(args.output_root).is_absolute()
        else Path(args.output_root),
        release_id=release_id,
        format_name=args.format,
        kaggle_id=args.kaggle_id,
        kaggle_title=args.kaggle_title,
        publish_kaggle=args.publish_kaggle,
        create_kaggle=args.create_kaggle,
        kaggle_message=args.kaggle_message,
    )
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
