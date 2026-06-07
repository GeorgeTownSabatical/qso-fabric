# Quantum Network Object (QNO) Spec

Generated from: `quantum_network_object_design_doc.rtf`
Status: Draft v1.0

## Scope
- Define a deterministic, replayable, auditable object model for quantum-network-ready workloads.
- Keep this object hardware-agnostic and policy-governed.
- Separate declarative quantum intent from physical backend execution.

## Canonical Object URIs
- `qso://quantum.state/<state_id>`
- `qso://quantum.node/<node_id>`
- `qso://quantum.entanglement/<entanglement_id>`
- `qso://quantum.network.channel/<channel_id>`
- `qso://quantum.logical_layer/<layer_id>`

## Canonical Schema
Reference schema file:
- `api/schemas/quantum_network_object.schema.json`

Required core semantics:
- `uri`, `session_id`, `policy_version`, `created_at`, `updated_at`
- `backend` and `qubit_count`
- `circuit_spec` and `measurement_schema`
- `verification_hash`

Optional but recommended:
- `backend_constraints`
- `circuit_hash`
- `logical_entanglement_graph`
- `classical_shadow`
- `error_model`
- `surface_code_layout`
- `execution_proof`
- `state_hash`

## Invariants
- No silent mutation: all state changes are event-sourced.
- Deterministic replay: identical event log must reconstruct identical state hash.
- Policy-gated execution: backend and workload constraints must be enforced before dispatch.
- Auditability: request/response metadata and verification hashes must be recorded.
- Separation of concerns: logical entanglement topology is declarative and not treated as remote physical entanglement over classical networks.

## Event Envelope (Minimum)
All QNO mutations should emit append-only events with:
- `schema_version`
- `event_id`
- `ts`
- `session_id`
- `actor`
- `kind`
- `object_uri`
- `payload`
- `prev_hash`
- `hash`
- `signature`

## Execution Flow
1. Validate schema and policy constraints.
2. Normalize circuit payload and compute `circuit_hash`.
3. Persist QNO mutation event.
4. Route to backend adapter.
5. Collect measurements and optional classical shadow.
6. Compute `verification_hash` and update `state_hash`.
7. Emit completion event.

## Security and Governance
- Use post-quantum-safe profile metadata at trust boundaries.
- Deny execution on unknown/unauthorized backends.
- Bind execution artifacts to signature + hash chain.
- Keep educational/sandbox execution isolated from production infra objects.

## Implementation Checklist

### P0: Contract and State
- [x] Add QNO schema file (`api/schemas/quantum_network_object.schema.json`)
- [x] Define canonical URI families (`quantum.state`, `quantum.node`, etc.)
- [ ] Add typed API model classes for QNO in `api/schemas/models.py`
- [ ] Add schema validation hooks during create/patch paths

### P1: Runtime and Events
- [ ] Add `services/quantum/manager.py`
- [ ] Add `services/quantum/replay_engine.py`
- [ ] Emit QNO events into append-only hash chain
- [ ] Add deterministic reducer for QNO state replay

### P2: Backend Abstraction
- [ ] Add `services/quantum/backends/base.py`
- [ ] Add `qiskit_backend.py`
- [ ] Add `cirq_backend.py`
- [ ] Add `photonic_backend.py`
- [ ] Add `remote_grpc_backend.py`
- [ ] Enforce backend capability handshake before execution

### P3: Entanglement + Logical Layer
- [ ] Add `qso://quantum.entanglement/*` object handlers
- [ ] Add `qso://quantum.logical_layer/*` object handlers
- [ ] Add logical-to-physical mapping abstraction
- [ ] Add measurement compatibility checks for graph gluing constraints

### P4: Tooling and APIs
- [ ] Add MCP tools (`qso.quantum_create`, `qso.quantum_execute`, `qso.quantum_measure`)
- [ ] Add REST endpoints for QNO create/read/execute/replay
- [ ] Add CLI commands for QNO lifecycle

### P5: Verification and Safety
- [ ] Add formal invariant tests (policy gates, replay determinism, hash-chain continuity)
- [ ] Add sandbox-only QNO execution profile
- [ ] Add quantum safety status reporting linkage

## Current Alignment Notes
Already present in repo and reusable:
- Governed transport/audit foundation under `services/transport/`
- Hash-chain event storage primitives under `storage/event_store/`
- MCP/REST scaffolding for extension under `api/mcp_tools/` and `api/rest/`
