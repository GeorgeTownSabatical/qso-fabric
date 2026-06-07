# Snapshot Nomenclature Contract

This repository uses two similarly named concepts that must stay distinct:

1. `snapshot` (singular): Python package namespace for snapshot compatibility and validation code.
2. `snapshots` (plural): filesystem artifact root for generated QFF exports and preview outputs.

## Canonical Terms

- Python namespace: `snapshot`
- Engine namespace: `snapshot_engine`
- Artifact directory: `snapshots/`

## Code-Level Guardrails

Use `core.naming.snapshot_terms` for shared constants and path resolution:

- `SNAPSHOT_PY_NAMESPACE`
- `SNAPSHOT_ENGINE_NAMESPACE`
- `SNAPSHOTS_ARTIFACTS_DIRNAME`
- `default_snapshot_artifacts_dir()`
- `resolve_snapshot_artifact_path(...)`

## Usage Rule

- Import modules from the singular namespace (`snapshot...`).
- Write generated files under the plural directory (`snapshots/...`).

Do not introduce alternate roots like `snapshot/` for filesystem artifacts.
