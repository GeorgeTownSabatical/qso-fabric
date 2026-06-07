# Mesh Handoff Contract (QSO Fabric)

## Scope
- Multi-instance coordination for shared state files under `.codex/state`.
- Applies to event logs, transport audit logs, bridge logs, sandbox op logs, and transport state snapshots.

## Writer Ownership
- Any instance may write shared artifacts, but all writes must acquire the artifact lock: `<artifact>.lock`.
- Locking is mandatory for:
  - `storage/event_store/JsonlEventStore.append`
  - `services/transport/NetworkAuditLogger.log`
  - `mcp_qso_edu/ConversationBridge.append`
  - `mcp_qso_edu/SandboxOperationStore.append_op`
  - `services/transport/TransportStateStore` read-modify-write flows

## Arbitration Rule
- Chain-linked logs (`*.jsonl`) arbitrate by tail hash under lock:
  - Read tail while lock is held.
  - Compute `prev_hash` from locked tail.
  - Append new row.
- State snapshots (`*.json`) arbitrate by lock + atomic replace:
  - Lock path.
  - Apply mutation against latest on-disk state.
  - Persist with atomic `os.replace`.

## Canonical Paths
- `QSO_EVENT_STORE_PATH` -> JSONL append-only store (preferred in mesh mode)
- `QSO_NETWORK_AUDIT_PATH` -> `.codex/state/network_audit.jsonl`
- `QSO_TRANSPORT_STATE_PATH` -> `.codex/state/transport_state.json`
- Plus bridge -> `.codex/state/plus_bridge.jsonl`
- Sandbox ops -> `.codex/state/mcp_qso_edu/sandboxes/<sandbox_id>.ops.jsonl`

## Compatibility Requirements
- Writers must preserve existing operation keys (`op`, `uri`, etc.) in sandbox logs.
- Additional metadata fields are allowed (`event_id`, `ts`, `prev_hash`, `hash`).
- Hash algorithm: SHA-256 over canonical JSON (`sort_keys=True`, `separators=(",", ":")`).

## Failure Handling
- If a chain is invalid:
  - Stop writes to that artifact.
  - Emit a local decision/audit event referencing the first invalid row index.
  - Require explicit operator action before resuming.
