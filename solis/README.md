# Solis Runtime

Solis is a deterministic, event-sourced stellar-economic runtime built directly on QSO Fabric.

## Stellar-Economic Mapping

Solis treats each economic domain as a star object (`qso://solis.star.<id>`). Economic deltas are mapped to stellar fields:

- `mass`: supply, collateral, and emission growth
- `luminosity`: throughput and value flow intensity
- `entropy_index`: governance and market disorder pressure
- `magnetic_field`: validator and coordination coherence
- `fusion_rate`: output efficiency (`luminosity / mass`)
- `collapse_probability`: bounded instability risk

## Deterministic Design

- Projection is pure (`project_stellar_v1`) with no randomness.
- All mutations go through `qso.patch(...)`.
- Every mutation emits immutable timeline entries and a derived stellar event object.
- Event hashes feed a rolling Merkle accumulator.
- Anchor epochs emit signed root events: `qso://solis.anchor.<epoch>`.

## Projection Mathematics

Given state `S` and delta `D`:

- `mass' = mass + D.mass`
- `luminosity' = luminosity + D.luminosity`
- `entropy' = entropy + D.entropy_index`
- `magnetic' = magnetic + D.magnetic_field`
- `core_temp' = mass' * ((1 / (1 + entropy')) * (mass' ** 0.1))`
- `fusion' = luminosity' / max(mass', 1e-9)`
- `collapse' = clamp(entropy' * (1 - magnetic') * fusion', 0, 1)`

## QSO Core Integration Points

Solis services use the QSO bridge surface:

- `qso.create(uri, schema)`
- `qso.read(uri)`
- `qso.patch(uri, delta)`
- `qso.timeline(uri)`
- `qso.entangle(uriA, uriB, relationship)`
- `qso.subscribe(uri|prefix)`

This keeps Solis domain code independent from lower-level registry/state-engine internals.

## Replay Verification Method

1. Apply the same ordered economic delta sequence to two Solis nodes.
2. Compare final star state hash.
3. Compare Merkle root and anchor payload hash.
4. Compare derived signal/reward payloads.

Solis test suite includes deterministic replay checks under `solis/tests`.

## QFF Snapshot Export Compatibility

Solis objects are standard QSO URIs and can be exported by existing QSO snapshot APIs:

- `qso_export_snapshot("qso://solis.star.<id>")`
- `qso_export_snapshot("qso://solis.constellation.<domain>")`

Replay reconstruction works from timeline data plus deterministic projector functions.
