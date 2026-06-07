from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_DB_PATH = Path(".codex/state/orange_county_apn/apn_orange_county_ca.sqlite3")
DEFAULT_HISTORY_CHECKPOINT_PATH = Path(".codex/state/orange_county_apn/history_checkpoint.json")
DEFAULT_SCOPE_SUMMARY_PATH = Path(".codex/state/orange_county_apn/scope_summary.json")

DOCS_AND_MAPS_BASE = "https://www.ocgis.com/survey/rest/services/WebApps/DocumentsandMaps/FeatureServer"
PARCEL_FEATURES_BASE = "https://www.ocgis.com/survey/rest/services/WebApps/ParcelFeatures/FeatureServer"
DOCS_AND_MAPS_UTILITY_BASE = (
    "https://utility.arcgis.com/usrsvcs/servers/6870e9fb3bba46529115be8fd19eda04/"
    "rest/services/OCLandInsights/DocumentsAndMaps/FeatureServer"
)
IRVINE_EASEMENTS_BASE = (
    "https://services.arcgis.com/UXmFoWC7yDHcDN5Q/arcgis/rest/services/Irvine_Easements/FeatureServer"
)


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    endpoint: str
    record_kind: str


SOURCE_SPECS = [
    SourceSpec("parcel_attributes", f"{PARCEL_FEATURES_BASE}/1", "parcel_attribute_snapshot"),
    SourceSpec("parcel_attribute_bridge", f"{PARCEL_FEATURES_BASE}/2", "parcel_attribute_bridge"),
    SourceSpec("doc_map_references", f"{DOCS_AND_MAPS_BASE}/9", "map_reference"),
    SourceSpec("doc_certificate_corrections", f"{DOCS_AND_MAPS_BASE}/8", "certificate_correction"),
    SourceSpec("doc_records_of_survey", f"{DOCS_AND_MAPS_BASE}/0", "record_of_survey"),
    SourceSpec("doc_parcel_map", f"{DOCS_AND_MAPS_BASE}/4", "parcel_map"),
    SourceSpec("doc_tract_map", f"{DOCS_AND_MAPS_BASE}/6", "tract_map"),
    SourceSpec("doc_lot_line_adjustment", f"{DOCS_AND_MAPS_BASE}/3", "lot_line_adjustment"),
    SourceSpec("doc_road_deed", f"{DOCS_AND_MAPS_BASE}/5", "road_deed"),
    SourceSpec("doc_misc_documents", f"{DOCS_AND_MAPS_BASE}/7", "misc_document"),
    SourceSpec("doc_tentative_maps", f"{DOCS_AND_MAPS_BASE}/10", "tentative_map"),
    SourceSpec("doc_city_annexation", f"{DOCS_AND_MAPS_BASE}/2", "city_annexation"),
    SourceSpec("doc_topographic_surveys", f"{DOCS_AND_MAPS_BASE}/11", "topographic_survey"),
    SourceSpec("doc_surveyor_maps", f"{DOCS_AND_MAPS_BASE}/12", "surveyor_map"),
    SourceSpec("doc_vacations_abandonments", f"{DOCS_AND_MAPS_UTILITY_BASE}/999045", "vacations_abandonments"),
    SourceSpec("easements_irvine", f"{IRVINE_EASEMENTS_BASE}/1", "easement"),
]


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_apn(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isalnum())


def _solis_hash(*parts: str) -> str:
    text = "|".join(parts).encode("utf-8")
    return hashlib.sha256(text).hexdigest()[:24]


def _solis_apn_id(apn_norm: str) -> str:
    return f"solis:oc:apn:{apn_norm}"


def _solis_fragment_id(source_id: str, source_objectid: int) -> str:
    return f"solis:oc:fragment:{source_id}:{source_objectid}"


def _solis_state_id(apn_norm: str, sequence: int) -> str:
    return f"solis:oc:state:{apn_norm}:{sequence:06d}"


def _solis_transition_id(apn_norm: str, from_sequence: int, to_sequence: int) -> str:
    return f"solis:oc:transition:{apn_norm}:{from_sequence:06d}:{to_sequence:06d}"


def _solis_anomaly_id(apn_norm: str, anomaly_type: str) -> str:
    return f"solis:oc:anomaly:{apn_norm}:{anomaly_type}"


def _request_json(url: str, *, timeout: float, retries: int, retry_sleep: float) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "qso-fabric-oc-scope/1.0"})
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


def _fetch_metadata(spec: SourceSpec, *, timeout: float, retries: int, retry_sleep: float) -> tuple[str, list[str]]:
    payload = _request_json(
        f"{spec.endpoint}?f=pjson",
        timeout=timeout,
        retries=retries,
        retry_sleep=retry_sleep,
    )
    object_id_field = str(payload.get("objectIdField", "")).strip()
    if not object_id_field:
        raise RuntimeError(f"objectIdField missing for {spec.source_id} ({spec.endpoint})")
    fields_raw = payload.get("fields", [])
    fields = [str(item.get("name")) for item in fields_raw if isinstance(item, dict) and item.get("name")]
    return object_id_field, fields


def _fetch_source_batch(
    *,
    spec: SourceSpec,
    object_id_field: str,
    last_objectid: int,
    batch_size: int,
    timeout: float,
    retries: int,
    retry_sleep: float,
) -> list[dict[str, Any]]:
    query = urlencode(
        {
            "where": f"{object_id_field} > {last_objectid}",
            "outFields": "*",
            "orderByFields": object_id_field,
            "returnGeometry": "false",
            "resultRecordCount": str(batch_size),
            "f": "json",
        }
    )
    payload = _request_json(
        f"{spec.endpoint}/query?{query}",
        timeout=timeout,
        retries=retries,
        retry_sleep=retry_sleep,
    )
    features = payload.get("features", [])
    if not isinstance(features, list):
        raise RuntimeError(f"features list missing for {spec.source_id}")
    rows: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        attrs = feature.get("attributes", {})
        if isinstance(attrs, dict):
            rows.append(attrs)
    return rows


def _extract_first(attrs: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = attrs.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _extract_event_date(attrs: dict[str, Any]) -> str | None:
    keys = [
        "RecordDate",
        "RECORDDATE",
        "DocRefDate",
        "SaleRecordDate",
        "DATEISSUED",
        "SurveyDate",
        "CertDate",
        "created_date",
        "last_edited_date",
    ]
    for key in keys:
        value = attrs.get(key)
        if value is None or value == "":
            continue
        if isinstance(value, (int, float)):
            raw = float(value)
            int_value = int(raw)
            text = str(abs(int_value))
            if len(text) == 8:
                try:
                    ymd = datetime.strptime(text, "%Y%m%d")
                    if 1800 <= ymd.year <= 2200:
                        return ymd.date().isoformat()
                except ValueError:
                    pass

            for divisor in (1.0, 1_000.0, 1_000_000.0):
                try:
                    dt = datetime.fromtimestamp(raw / divisor, tz=UTC)
                except (OverflowError, OSError, ValueError):
                    continue
                if 1800 <= dt.year <= 2200:
                    return dt.date().isoformat()
            continue
        text = str(value).strip()
        if not text:
            continue
        try:
            if text.endswith("Z"):
                return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
            return datetime.fromisoformat(text).date().isoformat()
        except ValueError:
            continue
    return None


def _load_checkpoint(path: Path, *, reset: bool) -> dict[str, Any]:
    if reset or not path.exists():
        now = _utc_now()
        return {
            "schema_version": "1.0",
            "created_at": now,
            "updated_at": now,
            "sources": {},
        }
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("history checkpoint must be a JSON object")
    loaded.setdefault("schema_version", "1.0")
    loaded.setdefault("created_at", _utc_now())
    loaded.setdefault("updated_at", _utc_now())
    loaded.setdefault("sources", {})
    if not isinstance(loaded["sources"], dict):
        raise ValueError("history checkpoint sources must be a JSON object")
    return loaded


def _write_checkpoint(path: Path, checkpoint: dict[str, Any]) -> None:
    checkpoint["updated_at"] = _utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS apn_records (
            objectid INTEGER PRIMARY KEY,
            assessment_no TEXT NOT NULL,
            assessment_no_norm TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS solis_source_fragments (
            source_id TEXT NOT NULL,
            source_objectid INTEGER NOT NULL,
            solis_fragment_id TEXT NOT NULL UNIQUE,
            fragment_hash TEXT NOT NULL,
            apn TEXT,
            apn_norm TEXT,
            legal_lot_id TEXT,
            map_num TEXT,
            doc_num TEXT,
            doc_type TEXT,
            event_date TEXT,
            payload_json TEXT,
            fetched_at_utc TEXT NOT NULL,
            PRIMARY KEY (source_id, source_objectid)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS solis_source_catalog (
            source_id TEXT PRIMARY KEY,
            endpoint TEXT NOT NULL,
            record_kind TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fragments_apn_norm
        ON solis_source_fragments (apn_norm)
        """
    )
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
        CREATE TABLE IF NOT EXISTS solis_apn_state (
            solis_state_id TEXT PRIMARY KEY,
            solis_apn_id TEXT NOT NULL,
            state_sequence INTEGER NOT NULL,
            event_date TEXT,
            source_id TEXT NOT NULL,
            source_objectid INTEGER NOT NULL,
            doc_num TEXT,
            map_num TEXT,
            legal_lot_id TEXT,
            solis_fragment_id TEXT NOT NULL,
            state_hash TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS solis_apn_transition (
            solis_transition_id TEXT PRIMARY KEY,
            solis_apn_id TEXT NOT NULL,
            from_state_id TEXT NOT NULL,
            to_state_id TEXT NOT NULL,
            transition_days INTEGER,
            trigger_doc_num TEXT,
            trigger_map_num TEXT
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS solis_apn_scope (
            solis_apn_id TEXT PRIMARY KEY,
            assessment_no TEXT NOT NULL,
            assessment_no_norm TEXT NOT NULL,
            fragment_count INTEGER NOT NULL,
            state_count INTEGER NOT NULL,
            transition_count INTEGER NOT NULL,
            anomaly_count INTEGER NOT NULL,
            first_event_date TEXT,
            last_event_date TEXT,
            has_easement_activity INTEGER NOT NULL,
            built_at_utc TEXT NOT NULL
        )
        """
    )


def _ingest_sources(
    *,
    db_path: Path,
    checkpoint_path: Path,
    source_specs: list[SourceSpec],
    batch_size: int,
    timeout: float,
    retries: int,
    retry_sleep: float,
    max_batches_per_source: int | None,
    reset_checkpoint: bool,
    store_payload_json: bool,
) -> dict[str, Any]:
    checkpoint = _load_checkpoint(checkpoint_path, reset=reset_checkpoint)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")

        if reset_checkpoint:
            with conn:
                conn.execute("DROP TABLE IF EXISTS solis_source_fragments")
                conn.execute("DROP TABLE IF EXISTS solis_source_catalog")
                conn.execute("DROP TABLE IF EXISTS solis_apn")
                conn.execute("DROP TABLE IF EXISTS solis_apn_state")
                conn.execute("DROP TABLE IF EXISTS solis_apn_transition")
                conn.execute("DROP TABLE IF EXISTS solis_apn_anomaly")
                conn.execute("DROP TABLE IF EXISTS solis_apn_scope")
            conn.execute("VACUUM")

        _ensure_tables(conn)
        source_stats: dict[str, dict[str, Any]] = {}

        for spec in source_specs:
            source_state = checkpoint["sources"].get(spec.source_id, {})
            if not isinstance(source_state, dict):
                source_state = {}
            source_state.setdefault("last_objectid", 0)
            source_state.setdefault("rows_written", 0)
            source_state.setdefault("batches_completed", 0)
            source_state["endpoint"] = spec.endpoint

            with conn:
                conn.execute(
                    """
                    INSERT INTO solis_source_catalog (source_id, endpoint, record_kind, updated_at_utc)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(source_id) DO UPDATE SET
                        endpoint=excluded.endpoint,
                        record_kind=excluded.record_kind,
                        updated_at_utc=excluded.updated_at_utc
                    """,
                    (spec.source_id, spec.endpoint, spec.record_kind, _utc_now()),
                )

            object_id_field, _ = _fetch_metadata(
                spec,
                timeout=timeout,
                retries=retries,
                retry_sleep=retry_sleep,
            )
            last_objectid = int(source_state["last_objectid"])
            batches_completed_this_run = 0
            rows_written_this_run = 0

            while True:
                if max_batches_per_source is not None and batches_completed_this_run >= max_batches_per_source:
                    break

                attrs_batch = _fetch_source_batch(
                    spec=spec,
                    object_id_field=object_id_field,
                    last_objectid=last_objectid,
                    batch_size=batch_size,
                    timeout=timeout,
                    retries=retries,
                    retry_sleep=retry_sleep,
                )
                if not attrs_batch:
                    break

                fetched_at = _utc_now()
                rows: list[tuple[Any, ...]] = []
                max_seen_objectid = last_objectid

                for attrs in attrs_batch:
                    raw_objectid = attrs.get(object_id_field)
                    if raw_objectid is None:
                        continue
                    source_objectid = int(raw_objectid)
                    max_seen_objectid = max(max_seen_objectid, source_objectid)

                    apn = _extract_first(
                        attrs,
                        [
                            "AssessmentNo",
                            "APN",
                            "APN_NO",
                            "APNNo",
                            "APN_NUMBER",
                            "Assessment_No",
                        ],
                    )
                    legal_lot_id = _extract_first(attrs, ["LegalLotID", "LegalLotId", "LocatedOn"])
                    map_num = _extract_first(
                        attrs,
                        [
                            "MapNum",
                            "MAPNUM",
                            "PMNum",
                            "TRNum",
                            "RoadDeedBookPage",
                            "BPNum",
                            "RefNum",
                        ],
                    )
                    doc_num = _extract_first(attrs, ["DocNum", "DocRefNo", "ORNum"])
                    doc_type = _extract_first(attrs, ["DocType", "Type"]) or spec.record_kind
                    event_date = _extract_event_date(attrs)
                    apn_norm = _normalize_apn(apn)
                    fragment_id = _solis_fragment_id(spec.source_id, source_objectid)
                    if store_payload_json:
                        payload_json = json.dumps(attrs, sort_keys=True)
                    else:
                        payload_json = None
                    fragment_hash = _solis_hash(
                        spec.source_id,
                        str(source_objectid),
                        str(apn_norm),
                        str(legal_lot_id or ""),
                        str(map_num or ""),
                        str(doc_num or ""),
                        str(doc_type or ""),
                        str(event_date or ""),
                    )

                    rows.append(
                        (
                            spec.source_id,
                            source_objectid,
                            fragment_id,
                            fragment_hash,
                            apn,
                            apn_norm,
                            legal_lot_id,
                            map_num,
                            doc_num,
                            doc_type,
                            event_date,
                            payload_json,
                            fetched_at,
                        )
                    )

                if max_seen_objectid <= last_objectid:
                    raise RuntimeError(f"non-advancing cursor for source {spec.source_id}")

                if rows:
                    with conn:
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
                            ON CONFLICT(source_id, source_objectid) DO UPDATE SET
                                solis_fragment_id=excluded.solis_fragment_id,
                                fragment_hash=excluded.fragment_hash,
                                apn=excluded.apn,
                                apn_norm=excluded.apn_norm,
                                legal_lot_id=excluded.legal_lot_id,
                                map_num=excluded.map_num,
                                doc_num=excluded.doc_num,
                                doc_type=excluded.doc_type,
                                event_date=excluded.event_date,
                                payload_json=excluded.payload_json,
                                fetched_at_utc=excluded.fetched_at_utc
                            """,
                            rows,
                        )

                last_objectid = max_seen_objectid
                source_state["last_objectid"] = last_objectid
                source_state["rows_written"] = int(source_state["rows_written"]) + len(rows)
                source_state["batches_completed"] = int(source_state["batches_completed"]) + 1
                checkpoint["sources"][spec.source_id] = source_state
                _write_checkpoint(checkpoint_path, checkpoint)

                batches_completed_this_run += 1
                rows_written_this_run += len(rows)
                print(
                    json.dumps(
                        {
                            "source_id": spec.source_id,
                            "batch": batches_completed_this_run,
                            "batch_rows": len(rows),
                            "last_objectid": last_objectid,
                        },
                        sort_keys=True,
                    )
                )
                if retry_sleep > 0:
                    time.sleep(retry_sleep)

            source_stats[spec.source_id] = {
                "rows_written_this_run": rows_written_this_run,
                "batches_completed_this_run": batches_completed_this_run,
                "last_objectid": source_state["last_objectid"],
                "rows_written_total": source_state["rows_written"],
                "batches_completed_total": source_state["batches_completed"],
            }
        return source_stats
    finally:
        conn.close()


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def build_scope(db_path: Path) -> dict[str, Any]:
    conn = sqlite3.connect(db_path)
    try:
        _ensure_tables(conn)
        now = _utc_now()

        with conn:
            conn.execute("DELETE FROM solis_apn")
            conn.execute("DELETE FROM solis_apn_state")
            conn.execute("DELETE FROM solis_apn_transition")
            conn.execute("DELETE FROM solis_apn_anomaly WHERE anomaly_type NOT LIKE 'live_%'")
            conn.execute("DELETE FROM solis_apn_scope")

        apn_rows = conn.execute(
            """
            SELECT apn_norm, MIN(apn) AS apn
            FROM (
                SELECT assessment_no_norm AS apn_norm, assessment_no AS apn
                FROM apn_records
                WHERE assessment_no_norm <> ''
                UNION ALL
                SELECT apn_norm, apn
                FROM solis_source_fragments
                WHERE apn_norm <> ''
            )
            GROUP BY apn_norm
            """
        ).fetchall()

        with conn:
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
                """,
                [(_solis_apn_id(norm), apn, norm, now, now) for norm, apn in apn_rows],
            )

        metrics = conn.execute(
            """
            SELECT
                f.apn_norm,
                MIN(f.event_date),
                MAX(f.event_date),
                COUNT(*) AS fragment_count,
                COUNT(DISTINCT CASE WHEN f.legal_lot_id IS NOT NULL AND TRIM(f.legal_lot_id) <> '' THEN f.legal_lot_id END) AS legal_lot_count,
                SUM(
                    CASE
                        WHEN lower(c.record_kind) IN ('road_deed', 'vacations_abandonments', 'easement')
                             OR lower(f.doc_type) LIKE '%deed%'
                             OR lower(f.doc_type) LIKE '%easement%'
                        THEN 1
                        ELSE 0
                    END
                ) AS easement_count
            FROM solis_source_fragments AS f
            LEFT JOIN solis_source_catalog AS c
                ON c.source_id = f.source_id
            WHERE f.apn_norm <> ''
            GROUP BY f.apn_norm
            """
        ).fetchall()
        with conn:
            conn.executemany(
                """
                UPDATE solis_apn
                SET
                    first_event_date = ?,
                    last_event_date = ?,
                    fragment_count = ?,
                    legal_lot_count = ?,
                    has_easement_activity = CASE WHEN ? > 0 THEN 1 ELSE 0 END,
                    updated_at_utc = ?
                WHERE assessment_no_norm = ?
                """,
                [
                    (
                        min_date,
                        max_date,
                        int(fragment_count or 0),
                        int(legal_lot_count or 0),
                        int(easement_count or 0),
                        now,
                        apn_norm,
                    )
                    for (
                        apn_norm,
                        min_date,
                        max_date,
                        fragment_count,
                        legal_lot_count,
                        easement_count,
                    ) in metrics
                ],
            )

        states: list[tuple[Any, ...]] = []
        transitions: list[tuple[Any, ...]] = []
        last_for_apn: dict[str, tuple[str, int, str | None, str | None, str | None]] = {}
        sequence_by_apn: dict[str, int] = {}

        cursor = conn.execute(
            """
            SELECT apn_norm, source_id, source_objectid, event_date, doc_num, map_num, legal_lot_id, solis_fragment_id
            FROM solis_source_fragments
            WHERE apn_norm <> '' AND event_date IS NOT NULL
            ORDER BY apn_norm, event_date, source_id, source_objectid
            """
        )
        for apn_norm, source_id, source_objectid, event_date, doc_num, map_num, legal_lot_id, fragment_id in cursor:
            sequence = sequence_by_apn.get(apn_norm, 0) + 1
            sequence_by_apn[apn_norm] = sequence
            apn_id = _solis_apn_id(apn_norm)
            state_id = _solis_state_id(apn_norm, sequence)
            state_hash = _solis_hash(
                apn_norm,
                str(event_date or ""),
                str(source_id),
                str(source_objectid),
                str(doc_num or ""),
                str(map_num or ""),
                str(legal_lot_id or ""),
            )
            states.append(
                (
                    state_id,
                    apn_id,
                    sequence,
                    event_date,
                    source_id,
                    int(source_objectid),
                    doc_num,
                    map_num,
                    legal_lot_id,
                    fragment_id,
                    state_hash,
                )
            )

            previous = last_for_apn.get(apn_norm)
            if previous is not None:
                prev_state_id, prev_sequence, prev_event_date, _, _ = previous
                transition_days: int | None = None
                prev_dt = _parse_date(prev_event_date)
                current_dt = _parse_date(event_date)
                if prev_dt is not None and current_dt is not None:
                    transition_days = (current_dt.date() - prev_dt.date()).days
                transition_id = _solis_transition_id(apn_norm, prev_sequence, sequence)
                transitions.append(
                    (
                        transition_id,
                        apn_id,
                        prev_state_id,
                        state_id,
                        transition_days,
                        doc_num,
                        map_num,
                    )
                )

            last_for_apn[apn_norm] = (state_id, sequence, event_date, doc_num, map_num)

        with conn:
            if states:
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
                    states,
                )
            if transitions:
                conn.executemany(
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
                    transitions,
                )

        anomalies: list[tuple[Any, ...]] = []
        detected_at = _utc_now()

        for apn_norm, legal_lot_count in conn.execute(
            """
            SELECT apn_norm, COUNT(DISTINCT legal_lot_id) AS legal_lot_count
            FROM solis_source_fragments
            WHERE apn_norm <> '' AND legal_lot_id IS NOT NULL AND TRIM(legal_lot_id) <> ''
            GROUP BY apn_norm
            HAVING legal_lot_count >= 4
            """
        ):
            severity = "high" if int(legal_lot_count) >= 10 else "medium"
            anomalies.append(
                (
                    _solis_anomaly_id(apn_norm, "high_legal_lot_fragmentation"),
                    _solis_apn_id(apn_norm),
                    "high_legal_lot_fragmentation",
                    severity,
                    float(legal_lot_count),
                    json.dumps({"legal_lot_count": int(legal_lot_count)}, sort_keys=True),
                    detected_at,
                )
            )

        for apn_norm, event_count, min_event, max_event in conn.execute(
            """
            SELECT apn_norm, COUNT(*) AS event_count, MIN(event_date), MAX(event_date)
            FROM solis_source_fragments
            WHERE apn_norm <> '' AND event_date IS NOT NULL
            GROUP BY apn_norm
            HAVING event_count >= 8
            """
        ):
            min_dt = _parse_date(min_event)
            max_dt = _parse_date(max_event)
            if min_dt is None or max_dt is None:
                continue
            span_days = (max_dt.date() - min_dt.date()).days
            if span_days <= 365:
                severity = "high" if int(event_count) >= 15 else "medium"
                anomalies.append(
                    (
                        _solis_anomaly_id(apn_norm, "high_event_velocity_365d"),
                        _solis_apn_id(apn_norm),
                        "high_event_velocity_365d",
                        severity,
                        float(event_count),
                        json.dumps(
                            {"event_count": int(event_count), "span_days": span_days},
                            sort_keys=True,
                        ),
                        detected_at,
                    )
                )

        for apn_norm, easement_count in conn.execute(
            """
            SELECT f.apn_norm, COUNT(*) AS easement_events
            FROM solis_source_fragments AS f
            LEFT JOIN solis_source_catalog AS c
                ON c.source_id = f.source_id
            WHERE f.apn_norm <> ''
              AND (
                    lower(c.record_kind) IN ('road_deed', 'vacations_abandonments', 'easement')
                    OR lower(f.doc_type) LIKE '%deed%'
                    OR lower(f.doc_type) LIKE '%easement%'
                  )
            GROUP BY f.apn_norm
            HAVING easement_events > 0
            """
        ):
            anomalies.append(
                (
                    _solis_anomaly_id(apn_norm, "easement_or_deed_activity"),
                    _solis_apn_id(apn_norm),
                    "easement_or_deed_activity",
                    "low",
                    float(easement_count),
                    json.dumps({"easement_events": int(easement_count)}, sort_keys=True),
                    detected_at,
                )
            )

        with conn:
            if anomalies:
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
                SELECT
                    a.solis_apn_id,
                    a.assessment_no,
                    a.assessment_no_norm,
                    a.fragment_count,
                    COALESCE(st.state_count, 0) AS state_count,
                    COALESCE(tr.transition_count, 0) AS transition_count,
                    COALESCE(an.anomaly_count, 0) AS anomaly_count,
                    a.first_event_date,
                    a.last_event_date,
                    a.has_easement_activity,
                    ?
                FROM solis_apn a
                LEFT JOIN (
                    SELECT solis_apn_id, COUNT(*) AS state_count
                    FROM solis_apn_state
                    GROUP BY solis_apn_id
                ) st ON st.solis_apn_id = a.solis_apn_id
                LEFT JOIN (
                    SELECT solis_apn_id, COUNT(*) AS transition_count
                    FROM solis_apn_transition
                    GROUP BY solis_apn_id
                ) tr ON tr.solis_apn_id = a.solis_apn_id
                LEFT JOIN (
                    SELECT solis_apn_id, COUNT(*) AS anomaly_count
                    FROM solis_apn_anomaly
                    GROUP BY solis_apn_id
                ) an ON an.solis_apn_id = a.solis_apn_id
                """,
                (now,),
            )

        summary = {
            "generated_at": _utc_now(),
            "db_path": str(db_path),
            "solis_apn_count": int(conn.execute("SELECT COUNT(*) FROM solis_apn").fetchone()[0]),
            "fragment_count": int(conn.execute("SELECT COUNT(*) FROM solis_source_fragments").fetchone()[0]),
            "state_count": int(conn.execute("SELECT COUNT(*) FROM solis_apn_state").fetchone()[0]),
            "transition_count": int(conn.execute("SELECT COUNT(*) FROM solis_apn_transition").fetchone()[0]),
            "anomaly_count": int(conn.execute("SELECT COUNT(*) FROM solis_apn_anomaly").fetchone()[0]),
            "scope_count": int(conn.execute("SELECT COUNT(*) FROM solis_apn_scope").fetchone()[0]),
        }
        return summary
    finally:
        conn.close()


def _write_summary(path: Path | None, summary: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _cmd_sync_history(args: argparse.Namespace) -> int:
    stats = _ingest_sources(
        db_path=args.db,
        checkpoint_path=args.checkpoint,
        source_specs=SOURCE_SPECS,
        batch_size=args.batch_size,
        timeout=args.timeout,
        retries=args.retries,
        retry_sleep=args.retry_sleep,
        max_batches_per_source=args.max_batches_per_source,
        reset_checkpoint=args.reset_checkpoint,
        store_payload_json=args.store_payload_json,
    )
    summary = {
        "db_path": str(args.db),
        "checkpoint_path": str(args.checkpoint),
        "source_stats": stats,
        "generated_at": _utc_now(),
    }
    _write_summary(args.summary, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _cmd_build_scope(args: argparse.Namespace) -> int:
    summary = build_scope(args.db)
    _write_summary(args.summary, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _cmd_run_all(args: argparse.Namespace) -> int:
    _ingest_sources(
        db_path=args.db,
        checkpoint_path=args.checkpoint,
        source_specs=SOURCE_SPECS,
        batch_size=args.batch_size,
        timeout=args.timeout,
        retries=args.retries,
        retry_sleep=args.retry_sleep,
        max_batches_per_source=args.max_batches_per_source,
        reset_checkpoint=args.reset_checkpoint,
        store_payload_json=args.store_payload_json,
    )
    summary = build_scope(args.db)
    _write_summary(args.summary, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile full-scope Orange County parcel intelligence for Solis AI: "
            "historical fragments, easements/deeds/maps, solis_ids, states, transitions, and anomalies."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite APN database path.")
    common.add_argument(
        "--summary",
        type=Path,
        default=DEFAULT_SCOPE_SUMMARY_PATH,
        help="Summary JSON output path.",
    )

    sync_cmd = sub.add_parser("sync-history", parents=[common], help="Sync historical and easement source fragments.")
    sync_cmd.add_argument(
        "--checkpoint",
        type=Path,
        default=DEFAULT_HISTORY_CHECKPOINT_PATH,
        help="Checkpoint JSON for source cursors.",
    )
    sync_cmd.add_argument("--batch-size", type=int, default=2000, help="Max records per source query batch.")
    sync_cmd.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds.")
    sync_cmd.add_argument("--retries", type=int, default=4, help="HTTP retries per request.")
    sync_cmd.add_argument("--retry-sleep", type=float, default=0.15, help="Retry/backoff base delay in seconds.")
    sync_cmd.add_argument(
        "--store-payload-json",
        action="store_true",
        help="Store full source payload JSON per fragment (significantly larger storage footprint).",
    )
    sync_cmd.add_argument(
        "--max-batches-per-source",
        type=int,
        default=None,
        help="Optional cap for controlled test runs.",
    )
    sync_cmd.add_argument("--reset-checkpoint", action="store_true", help="Reset history source checkpoint progress.")
    sync_cmd.set_defaults(func=_cmd_sync_history)

    build_cmd = sub.add_parser("build-scope", parents=[common], help="Build solis_id states/transitions/anomalies/scope tables.")
    build_cmd.set_defaults(func=_cmd_build_scope)

    run_cmd = sub.add_parser("run-all", parents=[common], help="Sync historical fragments and rebuild full Solis scope.")
    run_cmd.add_argument(
        "--checkpoint",
        type=Path,
        default=DEFAULT_HISTORY_CHECKPOINT_PATH,
        help="Checkpoint JSON for source cursors.",
    )
    run_cmd.add_argument("--batch-size", type=int, default=2000, help="Max records per source query batch.")
    run_cmd.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds.")
    run_cmd.add_argument("--retries", type=int, default=4, help="HTTP retries per request.")
    run_cmd.add_argument("--retry-sleep", type=float, default=0.15, help="Retry/backoff base delay in seconds.")
    run_cmd.add_argument(
        "--store-payload-json",
        action="store_true",
        help="Store full source payload JSON per fragment (significantly larger storage footprint).",
    )
    run_cmd.add_argument(
        "--max-batches-per-source",
        type=int,
        default=None,
        help="Optional cap for controlled test runs.",
    )
    run_cmd.add_argument("--reset-checkpoint", action="store_true", help="Reset history source checkpoint progress.")
    run_cmd.set_defaults(func=_cmd_run_all)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
