# Quantum Network Object Full Blueprint

Source: `quantum_network_object_design_doc.rtf`
Intent: import all major architectural tracks into the repo as actionable scaffolding.

## 1. Governed Transport Substrate
- Transport is first-class state (`qso://infra.transport`).
- Modes: `direct`, `vpn`, `tor`.
- Mandatory controls: policy gate, audit events, hash-chain logs, deterministic replay.
- Separation rules: research can be anonymous, capital execution cannot route over Tor by default.

Implemented scaffolds:
- `services/transport/*`
- `api/schemas/transport.schema.json`
- `tools/codexctl_transport.py`
- `.codex/state/network_audit.jsonl`

## 2. Sovereign Federation and Safety Layer
- Sidecar transport enforcement in K8s.
- Policy-version compatibility checks between nodes.
- Replay tolerance windows for nondeterministic network conditions.

Implemented scaffolds:
- `infra/docker/docker-compose.tor.yml`
- `infra/docker/docker-compose.vpn.yml`
- `infra/k8s/transport-sidecar.yaml`
- `infra/k8s/network-policy.yaml`

## 3. Sandboxed Educational MCP Layer
- Namespaced isolation (`qso://sandbox/<id>/...`).
- Capability-scoped operations.
- Rate-limited experimentation.
- No direct access to production transport/identity/global roots.

Implemented scaffolds:
- `mcp_qso_edu/*`
- `sandbox_mcp/*` (compatibility naming per doc)

## 4. Quantum Network State Object (QNSO/QNO)
- Canonical families:
  - `qso://quantum.state/*`
  - `qso://quantum.node/*`
  - `qso://quantum.entanglement/*`
  - `qso://quantum.network.channel/*`
  - `qso://quantum.logical_layer/*`
- Declarative model: circuit spec, logical entanglement graph, measurement schema, classical shadow, verification metadata.

Implemented scaffolds:
- `api/schemas/quantum_network_object.schema.json`
- `api/schemas/quantum_state.schema.json`
- `api/schemas/quantum_node.schema.json`
- `api/schemas/quantum_entanglement.schema.json`
- `api/schemas/quantum_network_channel.schema.json`
- `api/schemas/quantum_logical_layer.schema.json`

## 5. Quantum Backend Abstraction
- Hardware-neutral adapters and a manager execution path.
- Backends represented in code as adapters, not hard-coded infrastructure assumptions.

Implemented scaffolds:
- `services/quantum/backends/base.py`
- `services/quantum/backends/qiskit_backend.py`
- `services/quantum/backends/cirq_backend.py`
- `services/quantum/backends/photonic_backend.py`
- `services/quantum/backends/remote_grpc_backend.py`
- `services/quantum/manager.py`
- `services/quantum/replay_engine.py`

## 6. Quantum Job Federation Protocol (QJFP)
- Handshake abstraction includes node identity, hardware signature, policy version, and capability payload.

Implemented scaffold:
- `qso.quantum_qjfp_handshake(...)` in `api/mcp_tools/qso_tools.py`

## 7. Oracle and Compute-Economy Layer (QCU/QCC)
- QCU metering and provider scoring foundations.
- Settlement oracle scaffold for deterministic settlement records.

Implemented scaffolds:
- `services/qcc/qcu_meter.py`
- `services/qcc/provider_scoring.py`
- `services/qcc/token_model.py`
- `services/oracle/settlement_oracle.py`

## 8. Institutional Deployment Pack (QNSF)
- Namespace, deployment, service, ingress, autoscaling, secrets, sync job templates.

Implemented scaffolds:
- `infra/k8s/namespace.yaml`
- `infra/k8s/qnsf-deployment.yaml`
- `infra/k8s/oracle-deployment.yaml`
- `infra/k8s/registry-sync.yaml`
- `infra/k8s/ingress.yaml`
- `infra/k8s/service.yaml`
- `infra/k8s/hpa.yaml`
- `infra/k8s/secrets.yaml`

## 9. Next Hardening Pass (Remaining)
- Formal verification hooks for QNO invariants.
- Signed QNO execution artifacts with explicit PQ profile metadata.
- Cross-node consensus/reconciliation integration for quantum object updates.
- Full legal/governance document set for QCC issuance and redemption.
