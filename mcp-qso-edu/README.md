# mcp-qso-edu

Python implementation lives in `mcp_qso_edu/`.
This directory is a naming mirror for the architecture spec.

Run the MCP stdio bridge:

```bash
qso-edu-mcp-stdio
```

Enable upstream MCP app proxying (optional):

```bash
export QSO_EDU_UPSTREAM_APPS='{"example":["python3","/path/to/upstream_mcp.py"]}'
qso-edu-mcp-stdio --enable-upstream-apps
```

Shared message bridge tools:
- `bridge.append_message`
- `bridge.read_messages`

Canonical QSO chat tools:
- `qso.chat.open`
- `qso.chat.init`
- `qso.chat.append`
- `qso.chat.summarize`
- `qso.chat.verify`
- `qso.chat.tail`
- `qso.chat.read`
- `qso.chat.fork`

Security + governance:
- Ed25519 message signing (`mcp_qso_edu/crypto.py`)
- Author action permissions (`mcp_qso_edu/permissions.py::require_action`)

APC education tools (speculative-model governance):
- `qso.edu.apc.bootstrap` (generate full artifact bundle for audits/checklists/scorecards/pipeline/comparison/red-team)
- `qso.edu.apc.runs` (list generated APC runs for a sandbox)
- `qso.edu.apc.audit` (run deterministic quick/standard/exhaustive audit payload)
- `qso.edu.apc.resources` (load checklist, scorecard, controls, framework, red-team templates)

Every `qso.edu.apc.bootstrap` bundle now auto-includes:
- `validation/apc_bayes_comparison_latest.json`
- `validation/apc_bayes_comparison_latest.md`
(prior-sensitivity matrix + Bayes-factor robustness band)

APC resource endpoint:
- `qso://edu/apc`

Direct CLI wrapper (no JSON-RPC envelope):

```bash
qso-edu-apc-bootstrap --session-token apc-community --mode exhaustive
```
