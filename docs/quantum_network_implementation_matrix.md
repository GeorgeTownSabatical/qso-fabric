# Quantum Network Implementation Matrix

| Track | From Doc | Added in Repo | Status |
|---|---|---|---|
| Transport policy + adapters | Yes | `services/transport/*` | Scaffold + integrated |
| Transport CLI | Yes | `tools/codexctl_transport.py`, `tools/codexctl.py` | Integrated |
| Network audit hash chain | Yes | `.codex/state/network_audit.jsonl`, `services/transport/audit_logger.py` | Integrated |
| Sandbox MCP | Yes | `mcp_qso_edu/*`, `sandbox_mcp/*` | Integrated |
| Quantum state schema | Yes | `api/schemas/quantum_*` + `quantum_network_object.schema.json` | Added |
| Quantum manager/backends | Yes | `services/quantum/*` | Added |
| Quantum MCP methods | Yes | `api/mcp_tools/qso_tools.py` | Added |
| Oracle settlement scaffold | Yes | `services/oracle/settlement_oracle.py` | Added |
| QCU/QCC scaffolds | Yes | `services/qcc/*` | Added |
| Institutional K8s templates | Yes | `infra/k8s/{namespace,qnsf-deployment,oracle-deployment,registry-sync,ingress,service,hpa,secrets}.yaml` | Added |

## Notes
- "Added" means scaffold-level implementation with deterministic placeholders.
- Productionization requires policy/legal/compliance review and backend-specific integrations.
