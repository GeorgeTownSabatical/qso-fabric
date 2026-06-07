from __future__ import annotations

from collections import Counter, defaultdict
from math import ceil
from statistics import fmean
from typing import Any, Iterable, Mapping

from solis.telemetry import ExecutionTelemetryEvent


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, ceil(q * len(ordered)) - 1))
    return float(ordered[idx])


def _has_anomaly(flags: list[str]) -> bool:
    for flag in flags:
        normalized = str(flag).strip().lower()
        if normalized and normalized not in {"none", "normal", "ok"}:
            return True
    return False


def _summary(events: list[ExecutionTelemetryEvent]) -> dict[str, Any]:
    latencies = [float(row.latency_ms) for row in events]
    slippage = [float(row.slippage_bps) for row in events]
    reject_rates = [float(row.reject_rate) for row in events]
    drift_scores = [float(row.model_drift_score) for row in events]
    anomaly_flags = Counter(flag for row in events for flag in row.anomaly_flags if str(flag).strip())
    total = len(events)
    anomaly_events = sum(1 for row in events if _has_anomaly(row.anomaly_flags))

    return {
        "event_count": total,
        "latency_ms_avg": float(fmean(latencies)) if latencies else 0.0,
        "latency_ms_p95": _quantile(latencies, 0.95),
        "slippage_bps_avg": float(fmean(slippage)) if slippage else 0.0,
        "slippage_bps_p95": _quantile(slippage, 0.95),
        "reject_rate_avg": float(fmean(reject_rates)) if reject_rates else 0.0,
        "model_drift_avg": float(fmean(drift_scores)) if drift_scores else 0.0,
        "model_drift_p95": _quantile(drift_scores, 0.95),
        "anomaly_event_rate": float(anomaly_events / total) if total else 0.0,
        "anomaly_flag_counts": dict(sorted(anomaly_flags.items())),
    }


def _normalize_events(events: Iterable[ExecutionTelemetryEvent | Mapping[str, Any]]) -> list[ExecutionTelemetryEvent]:
    normalized: list[ExecutionTelemetryEvent] = []
    for row in events:
        if isinstance(row, ExecutionTelemetryEvent):
            normalized.append(row)
        else:
            normalized.append(ExecutionTelemetryEvent.model_validate(dict(row)))
    normalized.sort(key=lambda row: (row.metric_ts, row.event_id, row.strategy_id, row.venue, row.symbol))
    return normalized


def build_solis_telemetry_dashboards(
    events: Iterable[ExecutionTelemetryEvent | Mapping[str, Any]],
) -> dict[str, Any]:
    normalized = _normalize_events(events)
    by_strategy: dict[str, list[ExecutionTelemetryEvent]] = defaultdict(list)
    by_venue: dict[str, list[ExecutionTelemetryEvent]] = defaultdict(list)
    by_strategy_venue: dict[tuple[str, str], list[ExecutionTelemetryEvent]] = defaultdict(list)

    for row in normalized:
        by_strategy[row.strategy_id].append(row)
        by_venue[row.venue].append(row)
        by_strategy_venue[(row.strategy_id, row.venue)].append(row)

    window_start = normalized[0].metric_ts.isoformat() if normalized else None
    window_end = normalized[-1].metric_ts.isoformat() if normalized else None
    global_summary = _summary(normalized)

    strategy_rows = [
        {"strategy_id": strategy_id, **_summary(rows)}
        for strategy_id, rows in sorted(by_strategy.items())
    ]
    venue_rows = [{"venue": venue, **_summary(rows)} for venue, rows in sorted(by_venue.items())]
    strategy_venue_rows = [
        {"strategy_id": strategy_id, "venue": venue, **_summary(rows)}
        for (strategy_id, venue), rows in sorted(by_strategy_venue.items())
    ]

    return {
        "schema_version": "1.0",
        "dashboard_id": "solis_execution_quality_v1",
        "window_start": window_start,
        "window_end": window_end,
        "execution_quality": {
            "global": {
                "event_count": global_summary["event_count"],
                "latency_ms_avg": global_summary["latency_ms_avg"],
                "latency_ms_p95": global_summary["latency_ms_p95"],
                "slippage_bps_avg": global_summary["slippage_bps_avg"],
                "slippage_bps_p95": global_summary["slippage_bps_p95"],
                "reject_rate_avg": global_summary["reject_rate_avg"],
                "anomaly_event_rate": global_summary["anomaly_event_rate"],
            },
            "by_strategy": strategy_rows,
            "by_venue": venue_rows,
            "by_strategy_venue": strategy_venue_rows,
        },
        "model_drift": {
            "global": {
                "model_drift_avg": global_summary["model_drift_avg"],
                "model_drift_p95": global_summary["model_drift_p95"],
                "anomaly_flag_counts": global_summary["anomaly_flag_counts"],
            },
            "by_strategy": [
                {
                    "strategy_id": row["strategy_id"],
                    "model_drift_avg": row["model_drift_avg"],
                    "model_drift_p95": row["model_drift_p95"],
                    "anomaly_flag_counts": row["anomaly_flag_counts"],
                    "event_count": row["event_count"],
                }
                for row in strategy_rows
            ],
            "by_venue": [
                {
                    "venue": row["venue"],
                    "model_drift_avg": row["model_drift_avg"],
                    "model_drift_p95": row["model_drift_p95"],
                    "anomaly_flag_counts": row["anomaly_flag_counts"],
                    "event_count": row["event_count"],
                }
                for row in venue_rows
            ],
        },
    }
