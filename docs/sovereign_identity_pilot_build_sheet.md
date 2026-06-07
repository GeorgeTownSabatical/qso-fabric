# Sovereign Identity Pilot Build Sheet

Generated: 2026-02-14
Direction: Path 2 (`real-world pilot architecture`)

## Scope
- Build the first production-grade Sovereign Identity Runtime on top of QSO Fabric.
- Keep kernel invariants intact: append-only events, deterministic replay, signed events, policy pinning, entanglement lineage.
- Deliver a pilot topology that runs in zero-trust and air-gapped conditions.

## Assumptions
- `Good` is interpreted as `GDML` in this repository.
- Existing QSO runtime/event/policy/QFF primitives are baseline, not rewritten.
- Identity API schemas in `api/schemas/` are treated as contract inputs for implementation.

## Non-Negotiable Constraints
- No shared mutable central database.
- No unsigned state mutation.
- No direct identity state overwrite.
- No federation trust shortcut in verification path.
- Air-gap import must be strict archival validation, fail-closed.

## Pilot Target
- Primary pilot: enterprise authority cluster plus offline verifier enclave.
- Secondary pilot: sovereign personal vault node for offline continuity checks.
- Security posture: zero-trust between all nodes, including same organization boundaries.

## Task Graph

| ID | Task | Output | Depends On |
|---|---|---|---|
| T1 | Identity event taxonomy freeze | Canonical event enum + schema map | None |
| T2 | Identity reducer implementation | Deterministic reducer with replay | T1 |
| T3 | Identity object model | `qso://identity.person.<hash>` state envelope | T1 |
| T4 | Device and guardian link model | Entanglement relationship registry and revoke semantics | T1 |
| T5 | Authority node service | Credential issue/revoke, policy publish hooks | T2, T3 |
| T6 | Verifier node service | Bundle verify pipeline with deterministic replay | T2, T3, T4 |
| T7 | Offline bundle format | `/identity_bundle/` exporter/importer with signatures | T2, T4 |
| T8 | Trust-root lifecycle | trust root QSO, rotation and historical validity checks | T5, T6 |
| T9 | Governance activation engine | sovereign/multisig/democratic policy activation | T5, T8 |
| T10 | Node role binaries | `qso-identity-authority`, `qso-identity-verifier`, `qso-identity-observer`, `qso-identity-user` | T5, T6, T9 |
| T11 | End-to-end pilot tests | partition/adversarial/air-gap convergence suite | T6, T7, T9 |
| T12 | Pilot runbook and controls | deployment runbook, key ceremonies, incident response | T10, T11 |

## Milestone Plan

### M0: Kernel Identity Plane
- Deliver T1, T2, T3, T4.
- Event set includes:
`IDENTITY_CREATE`, `KEY_ROTATE`, `CREDENTIAL_ISSUE`, `CREDENTIAL_REVOKE`, `ENTITLEMENT_GRANT`, `ENTITLEMENT_REVOKE`, `LINK_ATTACH`, `LINK_REVOKE`, `MEASURE_VERIFY`, `IDENTITY_FREEZE`, `IDENTITY_ARCHIVE`.
- Acceptance gates:
- Reducer replay is deterministic across 3 nodes with identical event logs.
- Duplicate, non-monotonic, bad-signature, and wrong-policy events are rejected.
- Link revoke makes link inert without deleting lineage.

### M1: Product Runtime Plane
- Deliver T5, T6, T7.
- Verification flow is fixed:
1. Receive bundle.
2. Validate block hashes.
3. Validate signatures.
4. Validate policy version.
5. Validate revocation status.
6. Replay deterministically.
7. Compare replayed state hash to declared hash.
8. Accept or reject.
- Acceptance gates:
- Verifier succeeds in online and fully air-gapped mode.
- Tampered bundle is rejected at deterministic stage boundary with explicit reason.
- Snapshot import remains fail-closed.

### M2: Governance + Deployment Plane
- Deliver T8, T9, T10, T11, T12.
- Governance modes:
- Sovereign mode: single signer.
- Multi-sig mode: quorum activation index.
- Democratic mode: vote-event threshold activation.
- Acceptance gates:
- Policy rotation maintains historical validity windows.
- Partition and reconciliation preserve event/hash convergence.
- Observer node is audit-only and mutation denied by policy.

## Deployment Shape

### Cluster Roles
- Cluster A: Identity Authority.
- Cluster B: Enterprise verifier and relying-party edge.
- Cluster C: Personal sovereign vault.
- Air-Gap Node: offline verification and archive import.
- Anchor Node: checkpoint publisher.

### Exchange Rules
- Signed block exchange only.
- Policy handshake required before unknown policy application.
- Deterministic replay required before state acceptance.
- Trust-root mismatch blocks import and replication.

## Governance Posture

### Policy QSOs
- Policy objects are first-class QSOs.
- Activation events include activation index and effective-after boundary.
- No kernel mutation by governance mode switches.

### Trust Root QSOs
- Trust roots are represented as `qso://identity.trustroot.<domain>`.
- Rotation emits append-only events.
- Revocation preserves historical verification context.

## Pilot Exit Criteria (Go/No-Go)
- Go only if all are true:
- Deterministic replay parity across authority, verifier, and user nodes.
- Air-gap import strict mode rejects all invalid historical chains.
- Key rotation and trust-root rotation pass rollback and historical validity checks.
- Device compromise flow (`LINK_REVOKE`) isolates device without identity destruction.
- Guardian multi-sig policy gates sensitive mutations.
- Full verification path has no trust-by-membership shortcut.
- Adversarial injection tests converge with identical final state hash.

## First Sprint Execution Order
1. Implement T1-T4 in `core/identity` and `services/state_engine`.
2. Wire identity APIs from `api/schemas/qso_identity_openapi.yaml` into concrete services.
3. Implement bundle export/import strict archival mode for identity objects.
4. Add verifier pipeline and fail-closed reason taxonomy.
5. Add CI-collected identity tests under `tests/identity/` with `test_*.py` naming.

