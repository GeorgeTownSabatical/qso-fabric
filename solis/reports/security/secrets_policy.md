# Solis Secret Storage Policy

## Scope
This policy defines required handling for local secrets used by Solis adapters, CI lanes, and operator workflows.

## Required Storage Paths
- Local operator secrets: `~/.codex/state/secrets/`
- Repository code and tests must never embed live credentials.

## File Permission Requirements
- Secret files must be owner-only readable/writable (`chmod 600`).
- Secret directories must be owner-only (`chmod 700`) when feasible.

## Environment Variable Conventions
- Alpaca:
  - `APCA_API_BASE_URL`
  - `APCA_API_KEY_ID`
  - `APCA_API_SECRET_KEY`
- Optional live-order guardrails:
  - `SOLIS_ALPACA_LIVE_ORDER`
  - `SOLIS_ALPACA_ALLOW_LIVE`
  - `SOLIS_ALPACA_TEST_SYMBOL`
  - `SOLIS_ALPACA_TEST_NOTIONAL`

## Logging and Replay Constraints
- Secrets must not appear in:
  - QSO events
  - replay artifacts
  - test snapshots
  - CI logs
- Adapters may log response metadata, but must never emit secret header values.

## CI Secret Gating
- Live integration jobs must be conditionally enabled only when required secrets are present.
- Absence of secrets must produce a clean skip, not a failure.

## Rotation and Revocation
- Rotate credentials immediately if exposed in logs, commits, or shared transcripts.
- Revoke compromised keys before generating replacement credentials.
