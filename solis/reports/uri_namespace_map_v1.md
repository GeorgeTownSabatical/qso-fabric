# Solis URI Namespace Map v1

- Map file: `solis/schemas/uri_namespace_map.v1.json`
- Map version: `v1`
- Schema version: `1.0`
- Canonical hash (`sha256`): `6cbe9c0a15638a93b6da22904a2e96c68550cce0b79f8a3ecb92dbe5420cf7cb`

## Audit Procedure

1. Load `solis/schemas/uri_namespace_map.v1.json`.
2. Remove `audit.canonical_hash` from the payload.
3. Canonically serialize JSON (sorted keys, compact separators).
4. Compute `sha256`.
5. Compare with the recorded canonical hash.

## Coverage

The map defines canonical prefixes for identity, Solis runtime objects, policy/governance, RBAC audit, anchor events, and VR/AI runtime roots.
