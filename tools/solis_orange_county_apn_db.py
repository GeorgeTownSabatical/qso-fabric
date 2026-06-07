from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "https://ocgis.com/arcpub/rest/services/LegalLotsAttributeOpenData/FeatureServer/0"
DEFAULT_DB_PATH = Path(".codex/state/orange_county_apn/apn_orange_county_ca.sqlite3")
DEFAULT_CHECKPOINT_PATH = Path(".codex/state/orange_county_apn/checkpoint.json")
DEFAULT_SUMMARY_PATH = Path(".codex/state/orange_county_apn/summary.json")

DEFAULT_FIELDS = [
    "OBJECTID",
    "AssessmentNo",
    "LegalLotID",
    "Name",
    "LotType",
    "DocNum",
    "MapNum",
    "SiteAddress",
    "SiteCityState",
    "SiteZip5",
    "AssdAmt",
    "LandVal",
    "ImprovedVal",
    "GPLU_CODE",
    "GPLU_DESC",
    "ZCLASS",
]


BatchFetcher = Callable[[int], list[dict[str, Any]]]
SourceStatsFetcher = Callable[[], dict[str, int]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_apn(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum())


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        negative = cleaned.startswith("(") and cleaned.endswith(")")
        if negative:
            cleaned = cleaned[1:-1]
        cleaned = cleaned.replace("$", "").replace(",", "").strip()
        if not cleaned:
            return None
        try:
            number = float(cleaned)
        except ValueError:
            return None
        return -number if negative else number
    return float(value)


def _fetch_source_objectid_stats(
    *,
    endpoint: str,
    timeout: float,
    retries: int,
    retry_sleep: float,
) -> dict[str, int] | None:
    out_statistics = json.dumps(
        [
            {"statisticType": "min", "onStatisticField": "OBJECTID", "outStatisticFieldName": "min_objectid"},
            {"statisticType": "max", "onStatisticField": "OBJECTID", "outStatisticFieldName": "max_objectid"},
            {"statisticType": "count", "onStatisticField": "OBJECTID", "outStatisticFieldName": "row_count"},
        ],
        separators=(",", ":"),
    )
    query = urlencode(
        {
            "where": "AssessmentNo IS NOT NULL",
            "outStatistics": out_statistics,
            "returnGeometry": "false",
            "f": "json",
        }
    )
    payload = _request_json(
        f"{endpoint.rstrip('/')}/query?{query}",
        timeout=timeout,
        retries=retries,
        retry_sleep=retry_sleep,
    )
    features = payload.get("features", [])
    if not isinstance(features, list) or not features:
        return None
    first = features[0]
    if not isinstance(first, dict):
        return None
    attrs = first.get("attributes", {})
    if not isinstance(attrs, dict):
        return None

    row_count = attrs.get("row_count")
    min_objectid = attrs.get("min_objectid")
    max_objectid = attrs.get("max_objectid")
    if row_count in (None, ""):
        return None
    try:
        row_count_int = int(row_count)
    except (TypeError, ValueError):
        return None
    if row_count_int <= 0:
        return {"row_count": 0, "min_objectid": 0, "max_objectid": 0}
    if min_objectid in (None, "") or max_objectid in (None, ""):
        return None
    try:
        min_id_int = int(min_objectid)
        max_id_int = int(max_objectid)
    except (TypeError, ValueError):
        return None
    return {
        "row_count": row_count_int,
        "min_objectid": min_id_int,
        "max_objectid": max_id_int,
    }


def _read_local_objectid_stats(db_path: Path) -> dict[str, int] | None:
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*), MIN(objectid), MAX(objectid) FROM apn_records"
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    if not row:
        return None
    row_count = int(row[0] or 0)
    if row_count <= 0:
        return {"row_count": 0, "min_objectid": 0, "max_objectid": 0}
    min_objectid = row[1]
    max_objectid = row[2]
    if min_objectid is None or max_objectid is None:
        return None
    return {
        "row_count": row_count,
        "min_objectid": int(min_objectid),
        "max_objectid": int(max_objectid),
    }


def _ranges_overlap(*, left_min: int, left_max: int, right_min: int, right_max: int) -> bool:
    return not (left_max < right_min or right_max < left_min)


def _archive_rollover_artifacts(*, db_path: Path, checkpoint_path: Path) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_root = db_path.parent / "history_rollover"
    archive_root.mkdir(parents=True, exist_ok=True)

    archived: dict[str, str] = {}
    to_archive = {
        "db_archive_path": db_path,
        "checkpoint_archive_path": checkpoint_path,
    }
    for key, src in to_archive.items():
        if not src.exists():
            continue
        suffix = "".join(src.suffixes) or ".dat"
        stem = key.removesuffix("_path")
        candidate = archive_root / f"{stem}_{timestamp}{suffix}"
        counter = 1
        while candidate.exists():
            candidate = archive_root / f"{stem}_{timestamp}_{counter}{suffix}"
            counter += 1
        shutil.copy2(src, candidate)
        archived[key] = str(candidate)
    return archived


def _prune_rows_outside_source_window(
    conn: sqlite3.Connection,
    *,
    source_min_objectid: int,
    source_max_objectid: int,
) -> dict[str, int]:
    pruned_below = conn.execute(
        "DELETE FROM apn_records WHERE objectid < ?",
        (source_min_objectid,),
    ).rowcount
    pruned_above = conn.execute(
        "DELETE FROM apn_records WHERE objectid > ?",
        (source_max_objectid,),
    ).rowcount
    return {
        "pruned_rows_below_source_min": int(pruned_below if pruned_below is not None and pruned_below >= 0 else 0),
        "pruned_rows_above_source_max": int(pruned_above if pruned_above is not None and pruned_above >= 0 else 0),
    }


def _request_json(url: str, *, timeout: float, retries: int, retry_sleep: float) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "qso-fabric-oc-apn-sync/1.0"})
            with urlopen(req, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict) and "error" in payload:
                raise RuntimeError(json.dumps(payload["error"], sort_keys=True))
            if not isinstance(payload, dict):
                raise RuntimeError("unexpected non-object JSON response")
            return payload
        except (HTTPError, URLError, OSError, ValueError, RuntimeError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(retry_sleep * (attempt + 1))
    raise RuntimeError(f"request failed after retries for {url}: {last_error}") from last_error


def _fetch_batch_from_endpoint(
    *,
    endpoint: str,
    last_object_id: int,
    batch_size: int,
    fields: list[str],
    timeout: float,
    retries: int,
    retry_sleep: float,
) -> list[dict[str, Any]]:
    query = urlencode(
        {
            "where": f"OBJECTID > {last_object_id} AND AssessmentNo IS NOT NULL",
            "outFields": ",".join(fields),
            "returnGeometry": "false",
            "orderByFields": "OBJECTID",
            "resultRecordCount": str(batch_size),
            "f": "json",
        }
    )
    payload = _request_json(
        f"{endpoint.rstrip('/')}/query?{query}",
        timeout=timeout,
        retries=retries,
        retry_sleep=retry_sleep,
    )
    features = payload.get("features", [])
    if not isinstance(features, list):
        raise RuntimeError("query response missing features list")
    out: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        attrs = feature.get("attributes", {})
        if isinstance(attrs, dict):
            out.append(attrs)
    return out


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS apn_records (
            objectid INTEGER PRIMARY KEY,
            assessment_no TEXT NOT NULL,
            assessment_no_norm TEXT NOT NULL,
            legal_lot_id TEXT,
            parcel_name TEXT,
            lot_type TEXT,
            doc_num TEXT,
            map_num TEXT,
            site_address TEXT,
            site_city_state TEXT,
            site_zip5 TEXT,
            assd_amt REAL,
            land_val REAL,
            improved_val REAL,
            gplu_code TEXT,
            gplu_desc TEXT,
            zclass TEXT,
            fetched_at_utc TEXT NOT NULL,
            source_endpoint TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apn_records_assessment_no
        ON apn_records (assessment_no)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apn_records_assessment_no_norm
        ON apn_records (assessment_no_norm)
        """
    )
    conn.execute(
        """
        CREATE VIEW IF NOT EXISTS apn_unique AS
        SELECT
            assessment_no,
            assessment_no_norm,
            MIN(objectid) AS representative_objectid,
            COUNT(*) AS row_count
        FROM apn_records
        GROUP BY assessment_no, assessment_no_norm
        """
    )


def _load_checkpoint(path: Path, *, endpoint: str, reset: bool) -> dict[str, Any]:
    if reset or not path.exists():
        now = _utc_now()
        return {
            "schema_version": "1.0",
            "created_at": now,
            "updated_at": now,
            "endpoint": endpoint,
            "last_objectid": 0,
            "batches_completed": 0,
            "rows_written": 0,
        }

    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("checkpoint must be a JSON object")

    loaded.setdefault("schema_version", "1.0")
    loaded.setdefault("created_at", _utc_now())
    loaded.setdefault("updated_at", _utc_now())
    loaded.setdefault("endpoint", endpoint)
    loaded.setdefault("last_objectid", 0)
    loaded.setdefault("batches_completed", 0)
    loaded.setdefault("rows_written", 0)

    if str(loaded.get("endpoint")) != endpoint:
        loaded["endpoint"] = endpoint
        loaded["last_objectid"] = 0
        loaded["batches_completed"] = 0
        loaded["rows_written"] = 0

    return loaded


def _write_checkpoint(path: Path, checkpoint: dict[str, Any]) -> None:
    checkpoint["updated_at"] = _utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _row_from_attributes(attrs: dict[str, Any], *, endpoint: str, fetched_at: str) -> tuple[Any, ...] | None:
    object_id = attrs.get("OBJECTID")
    apn = str(attrs.get("AssessmentNo", "")).strip()
    if object_id is None or not apn:
        return None

    normalized = _normalize_apn(apn)
    return (
        int(object_id),
        apn,
        normalized,
        attrs.get("LegalLotID"),
        attrs.get("Name"),
        attrs.get("LotType"),
        attrs.get("DocNum"),
        attrs.get("MapNum"),
        attrs.get("SiteAddress"),
        attrs.get("SiteCityState"),
        attrs.get("SiteZip5"),
        _to_float(attrs.get("AssdAmt")),
        _to_float(attrs.get("LandVal")),
        _to_float(attrs.get("ImprovedVal")),
        attrs.get("GPLU_CODE"),
        attrs.get("GPLU_DESC"),
        attrs.get("ZCLASS"),
        fetched_at,
        endpoint,
    )


def _upsert_rows(conn: sqlite3.Connection, rows: list[tuple[Any, ...]]) -> None:
    conn.executemany(
        """
        INSERT INTO apn_records (
            objectid,
            assessment_no,
            assessment_no_norm,
            legal_lot_id,
            parcel_name,
            lot_type,
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(objectid) DO UPDATE SET
            assessment_no=excluded.assessment_no,
            assessment_no_norm=excluded.assessment_no_norm,
            legal_lot_id=excluded.legal_lot_id,
            parcel_name=excluded.parcel_name,
            lot_type=excluded.lot_type,
            doc_num=excluded.doc_num,
            map_num=excluded.map_num,
            site_address=excluded.site_address,
            site_city_state=excluded.site_city_state,
            site_zip5=excluded.site_zip5,
            assd_amt=excluded.assd_amt,
            land_val=excluded.land_val,
            improved_val=excluded.improved_val,
            gplu_code=excluded.gplu_code,
            gplu_desc=excluded.gplu_desc,
            zclass=excluded.zclass,
            fetched_at_utc=excluded.fetched_at_utc,
            source_endpoint=excluded.source_endpoint
        """,
        rows,
    )


def _summarize(conn: sqlite3.Connection, *, endpoint: str, db_path: Path) -> dict[str, Any]:
    total_rows = int(conn.execute("SELECT COUNT(*) FROM apn_records").fetchone()[0])
    total_distinct_apn = int(
        conn.execute(
            "SELECT COUNT(DISTINCT assessment_no_norm) FROM apn_records WHERE assessment_no_norm <> ''"
        ).fetchone()[0]
    )
    min_objectid, max_objectid = conn.execute(
        "SELECT MIN(objectid), MAX(objectid) FROM apn_records"
    ).fetchone()
    null_city_rows = int(
        conn.execute("SELECT COUNT(*) FROM apn_records WHERE site_city_state IS NULL OR TRIM(site_city_state) = ''").fetchone()[0]
    )
    return {
        "db_path": str(db_path),
        "endpoint": endpoint,
        "total_rows": total_rows,
        "total_distinct_apn": total_distinct_apn,
        "min_objectid": min_objectid,
        "max_objectid": max_objectid,
        "rows_missing_city": null_city_rows,
        "generated_at": _utc_now(),
    }


def _write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sync_apn_database(
    *,
    endpoint: str,
    db_path: Path,
    checkpoint_path: Path,
    summary_path: Path | None,
    batch_size: int,
    timeout: float,
    retries: int,
    retry_sleep: float,
    max_batches: int | None,
    reset_checkpoint: bool,
    full_refresh: bool,
    fields: list[str],
    fetcher: BatchFetcher | None = None,
    source_stats_fetcher: SourceStatsFetcher | None = None,
    auto_reset_on_source_rollover: bool = True,
    archive_on_rollover: bool = True,
) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = _load_checkpoint(checkpoint_path, endpoint=endpoint, reset=reset_checkpoint or full_refresh)
    source_stats: dict[str, int] | None = None
    pre_sync_local_stats: dict[str, int] | None = None
    rollover_detected = False
    rollover_reason = ""
    rollover_artifacts: dict[str, str] = {}

    if full_refresh and db_path.exists():
        db_path.unlink()
    elif auto_reset_on_source_rollover:
        pre_sync_local_stats = _read_local_objectid_stats(db_path)
        if source_stats_fetcher is not None:
            source_stats = source_stats_fetcher()
        elif fetcher is None:
            source_stats = _fetch_source_objectid_stats(
                endpoint=endpoint,
                timeout=timeout,
                retries=retries,
                retry_sleep=retry_sleep,
            )

        if (
            source_stats is not None
            and pre_sync_local_stats is not None
            and source_stats["row_count"] > 0
            and pre_sync_local_stats["row_count"] > 0
        ):
            overlap = _ranges_overlap(
                left_min=pre_sync_local_stats["min_objectid"],
                left_max=pre_sync_local_stats["max_objectid"],
                right_min=source_stats["min_objectid"],
                right_max=source_stats["max_objectid"],
            )
            if not overlap:
                rollover_detected = True
                rollover_reason = (
                    "local OBJECTID window "
                    f"{pre_sync_local_stats['min_objectid']}-{pre_sync_local_stats['max_objectid']} "
                    "does not overlap source window "
                    f"{source_stats['min_objectid']}-{source_stats['max_objectid']}"
                )
                if archive_on_rollover:
                    rollover_artifacts = _archive_rollover_artifacts(
                        db_path=db_path,
                        checkpoint_path=checkpoint_path,
                    )
                if db_path.exists():
                    db_path.unlink()
                checkpoint = _load_checkpoint(checkpoint_path, endpoint=endpoint, reset=True)

    conn = sqlite3.connect(db_path)
    try:
        _ensure_schema(conn)
        pruning_stats = {
            "pruned_rows_below_source_min": 0,
            "pruned_rows_above_source_max": 0,
        }
        if (
            source_stats is not None
            and source_stats["row_count"] > 0
            and not rollover_detected
        ):
            with conn:
                pruning_stats = _prune_rows_outside_source_window(
                    conn,
                    source_min_objectid=source_stats["min_objectid"],
                    source_max_objectid=source_stats["max_objectid"],
                )
            checkpoint_last_objectid = int(checkpoint.get("last_objectid", 0))
            if (
                pruning_stats["pruned_rows_above_source_max"] > 0
                and checkpoint_last_objectid > source_stats["max_objectid"]
            ):
                checkpoint["last_objectid"] = max(0, source_stats["min_objectid"] - 1)
                _write_checkpoint(checkpoint_path, checkpoint)

        last_objectid = int(checkpoint.get("last_objectid", 0))
        sync_batches_completed = 0
        sync_rows_written = 0

        while True:
            if max_batches is not None and sync_batches_completed >= max_batches:
                break

            if fetcher is None:
                attrs_batch = _fetch_batch_from_endpoint(
                    endpoint=endpoint,
                    last_object_id=last_objectid,
                    batch_size=batch_size,
                    fields=fields,
                    timeout=timeout,
                    retries=retries,
                    retry_sleep=retry_sleep,
                )
            else:
                attrs_batch = fetcher(last_objectid)

            if not attrs_batch:
                break

            fetched_at = _utc_now()
            rows: list[tuple[Any, ...]] = []
            max_seen_objectid = last_objectid

            for attrs in attrs_batch:
                row = _row_from_attributes(attrs, endpoint=endpoint, fetched_at=fetched_at)
                if row is None:
                    continue
                rows.append(row)
                max_seen_objectid = max(max_seen_objectid, int(row[0]))

            if max_seen_objectid <= last_objectid:
                raise RuntimeError("non-advancing OBJECTID cursor detected during sync")

            if rows:
                with conn:
                    _upsert_rows(conn, rows)
                sync_rows_written += len(rows)

            last_objectid = max_seen_objectid
            sync_batches_completed += 1
            checkpoint["last_objectid"] = last_objectid
            checkpoint["batches_completed"] = int(checkpoint.get("batches_completed", 0)) + 1
            checkpoint["rows_written"] = int(checkpoint.get("rows_written", 0)) + len(rows)
            _write_checkpoint(checkpoint_path, checkpoint)

            print(
                json.dumps(
                    {
                        "batch": sync_batches_completed,
                        "batch_rows": len(rows),
                        "last_objectid": last_objectid,
                    },
                    sort_keys=True,
                )
            )

            if retry_sleep > 0:
                time.sleep(retry_sleep)

        summary = _summarize(conn, endpoint=endpoint, db_path=db_path)
        summary["sync_rows_written"] = sync_rows_written
        summary["sync_batches_completed"] = sync_batches_completed
        summary["checkpoint_path"] = str(checkpoint_path)
        summary["checkpoint_last_objectid"] = last_objectid
        summary["rollover_detected"] = rollover_detected
        summary.update(pruning_stats)
        if rollover_reason:
            summary["rollover_reason"] = rollover_reason
        summary.update(rollover_artifacts)
        if pre_sync_local_stats is not None:
            summary["pre_sync_local_row_count"] = pre_sync_local_stats["row_count"]
            summary["pre_sync_local_min_objectid"] = pre_sync_local_stats["min_objectid"]
            summary["pre_sync_local_max_objectid"] = pre_sync_local_stats["max_objectid"]
        if source_stats is not None:
            summary["source_row_count"] = source_stats["row_count"]
            summary["source_min_objectid"] = source_stats["min_objectid"]
            summary["source_max_objectid"] = source_stats["max_objectid"]

        if summary_path is not None:
            _write_summary(summary_path, summary)
        return summary
    finally:
        conn.close()


def _cmd_sync(args: argparse.Namespace) -> int:
    summary = sync_apn_database(
        endpoint=args.endpoint,
        db_path=args.db,
        checkpoint_path=args.checkpoint,
        summary_path=args.summary,
        batch_size=args.batch_size,
        timeout=args.timeout,
        retries=args.retries,
        retry_sleep=args.retry_sleep,
        max_batches=args.max_batches,
        reset_checkpoint=args.reset_checkpoint,
        full_refresh=args.full_refresh,
        fields=DEFAULT_FIELDS,
        auto_reset_on_source_rollover=args.auto_reset_on_source_rollover,
        archive_on_rollover=args.archive_on_rollover,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    if not args.db.exists():
        raise SystemExit(f"database does not exist: {args.db}")
    conn = sqlite3.connect(args.db)
    try:
        summary = _summarize(conn, endpoint=args.endpoint, db_path=args.db)
    finally:
        conn.close()
    if args.summary is not None:
        _write_summary(args.summary, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and maintain a full Orange County, CA APN database from public ArcGIS parcel records."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sync_cmd = sub.add_parser("sync", help="Sync APN records from Orange County public ArcGIS service.")
    sync_cmd.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="ArcGIS FeatureServer layer endpoint.")
    sync_cmd.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite database output path.")
    sync_cmd.add_argument(
        "--checkpoint",
        type=Path,
        default=DEFAULT_CHECKPOINT_PATH,
        help="Checkpoint JSON path for incremental cursor progress.",
    )
    sync_cmd.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY_PATH, help="Summary JSON output path.")
    sync_cmd.add_argument("--batch-size", type=int, default=2000, help="Max records per ArcGIS query batch.")
    sync_cmd.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout (seconds).")
    sync_cmd.add_argument("--retries", type=int, default=4, help="HTTP retries per request.")
    sync_cmd.add_argument(
        "--retry-sleep",
        type=float,
        default=0.15,
        help="Base retry sleep in seconds (also used as batch pacing delay).",
    )
    sync_cmd.add_argument("--max-batches", type=int, default=None, help="Optional cap on batches for controlled runs.")
    sync_cmd.add_argument("--reset-checkpoint", action="store_true", help="Reset cursor checkpoint and start from OBJECTID 0.")
    sync_cmd.add_argument("--full-refresh", action="store_true", help="Delete existing DB file and rebuild from scratch.")
    sync_cmd.add_argument(
        "--auto-reset-on-source-rollover",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Detect non-overlapping OBJECTID windows between local DB and source and reset automatically "
            "(use --no-auto-reset-on-source-rollover to disable)."
        ),
    )
    sync_cmd.add_argument(
        "--archive-on-rollover",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Archive prior DB/checkpoint before automatic rollover reset "
            "(use --no-archive-on-rollover to disable)."
        ),
    )
    sync_cmd.set_defaults(func=_cmd_sync)

    stats_cmd = sub.add_parser("stats", help="Read summary stats from a local APN database.")
    stats_cmd.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite database path.")
    stats_cmd.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Endpoint label for emitted summary.")
    stats_cmd.add_argument("--summary", type=Path, default=None, help="Optional summary JSON output path.")
    stats_cmd.set_defaults(func=_cmd_stats)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
