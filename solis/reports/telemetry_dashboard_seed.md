# Solis Telemetry Dashboard Seed (T0210)

This seed dashboard focuses on execution quality and model drift from execution telemetry events.

## Source

- Builder: `observability/dashboards/solis_telemetry.py`
- Entry point: `build_solis_telemetry_dashboards(events)`

## Global Execution Quality Metrics

- `event_count`
- `latency_ms_avg`, `latency_ms_p95`
- `slippage_bps_avg`, `slippage_bps_p95`
- `reject_rate_avg`
- `anomaly_event_rate`

## Global Model Drift Metrics

- `model_drift_avg`, `model_drift_p95`
- `anomaly_flag_counts`

## Dimension Mapping

Execution quality and drift are emitted for:

- `by_strategy` (`strategy_id`)
- `by_venue` (`venue`)
- `by_strategy_venue` (`strategy_id`, `venue`)

All rows are sorted deterministically so repeated runs with identical inputs produce identical outputs.
