# Solis Versioning Conventions

This document is the canonical versioning policy for governed Solis artifacts.

## Version Fields

- `schema_version` (required): Required on all governed JSON schemas and state artifacts.
- `policy_version` (required for governance-bound decisions): Policy document version, formatted `v<major>`.
- `model_version` (required for model-derived outputs): Model generation version, formatted `major.minor`.
- `compiler_version` (required for DSL compiled outputs): Compiler generation version, formatted `major.minor`.

## Compatibility Policy

- Schema compatibility is `major.minor`.
- Backward compatible updates must keep `major` unchanged and increase `minor`.
- Any `major` bump is breaking and requires explicit migration handling.
- Policy versions are monotonic (`v1`, `v2`, ...). Rollback is allowed only by explicit governance action.

## Enforcement Scope

- `solis/schemas/*.schema.json` enforces `schema_version` presence.
- Runtime helpers in `solis/schemas/versioning.py` provide deterministic parsing and compatibility checks.
- CI/tests must fail if a governed schema omits required version fields.
