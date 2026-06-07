# Deployment Target Decision

Date: 2026-02-18

## Selected Default

- Primary default: **local durable mode**
- Runtime persistence:
  - `QSO_EVENT_STORE_PATH=/var/lib/qso/events/events.jsonl`
  - `QSO_CHECKPOINT_STORE_PATH=/var/lib/qso/checkpoints/checkpoints.json`
  - `QSO_SNAPSHOT_STORE_DIR=/var/lib/qso/snapshots`

## Cluster-Ready Path

- Kubernetes deployment now includes:
  - persistent volume claim (`qso-fabric-pvc`)
  - volume mount at `/var/lib/qso`
  - persistent store env wiring
  - container args for HTTP service mode

## Rationale

- Local durable mode provides immediate persistence without additional infrastructure.
- The updated Kubernetes manifest provides a direct migration path for multi-node deployment.
