# qso-fabric

QSO-Fabric is an event-sourced continuity substrate for auditable reasoning,
quantum-inspired state analysis, MCP tool execution, QFF snapshots, identity
state, transport controls, and public-facing automation surfaces.

The core idea is simple: a Quantum State Object is not just a stored vector or
record. It is a continuity-bearing object whose state can be observed, recalled,
contradicted, repaired, trusted, projected, algebraically transformed, replayed,
and verified through deterministic event history.

This repository provides:

- event-sourced QSO runtime with replayable state transitions
- MCP tool surface for local and federated automation
- QFF snapshot export/import
- deterministic quantum-network object execution
- QSO-Fabric local-to-global gluing/coherence analysis
- Quantum LISP reasoning programs compiled into auditable IR
- Qiskit, PennyLane, Cirq, and ITensor backend adapters with deterministic fallbacks
- identity, transport, snapshot, visualization, and meta-learning primitives
- Solis property/APN automation and investigation-oriented graph workflows

Public site:

- GitHub repo: <https://github.com/GeorgeTownSabatical/qso-fabric>
- GitHub Pages: <https://georgetownsabatical.github.io/qso-fabric/>

## Architecture At A Glance

QSO-Fabric is organized around five cooperating layers:

1. State runtime: `services/state_engine`, `services/event_log`, and replay tools
   maintain append-only object history.
2. Quantum object layer: `services/quantum` executes circuit jobs, fabric gluing,
   backend diagnostics, and replay.
3. Quantum LISP layer: `services/quantum_lisp` compiles symbolic reasoning
   programs into deterministic JSON-safe IR and descriptive analysis reports.
4. Tool surfaces: `api/mcp_tools`, `mcp_server`, CLIs, and websocket helpers expose
   the runtime to local agents and external automation.
5. Domain workflows: Solis, investigation graph engines, APN pipelines, snapshots,
   and visualization packages consume the shared substrate instead of defining
   parallel state systems.

The runtime is designed to be useful even when optional quantum libraries are not
installed. Qiskit, PennyLane, Cirq, and ITensor paths all return stable result
shapes with deterministic fallbacks, so automation can rely on the contract first
and opportunistically use native engines when present.

## Living Wiki, Executable State

A folder-based AI wiki is already a powerful second brain: raw sources go in,
linked notes come out, and future questions start from accumulated context
instead of a blank chat.

QSO-Fabric extends that pattern from "living wiki" to "executable continuity":

- sources become replayable QSO events, not just static notes
- contradictions are scored and retained as useful signal
- repairs are explicit proposals until a commit boundary exists
- reasoning traces carry compiled IR, backend diagnostics, and verification hashes
- benchmarks make engine behavior measurable instead of merely impressive

The result is a knowledge system that can read, remember, explain, test, replay,
and publish its own reasoning surface.

## Quickstart

```bash
cd /Users/ALISTAIRE/qso-fabric
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
make test
python main.py
```

## Quantum LISP Reasoning Engine

Quantum LISP is the symbolic reasoning layer for QSO-Fabric. It accepts small
S-expression programs, validates that they stay inside the descriptive calculus,
compiles them into auditable IR, projects them into QSO fabric patches/overlaps,
runs selected backend diagnostics, and persists a `reasoning_trace`.

Allowed v1 forms:

- `defintent`
- `observe`
- `hypothesis`
- `entangle`
- `contradict`
- `repair`
- `project`
- `trust`
- `algebra`
- `reason`

Forbidden v1 forms:

- `commit`
- `measure-state`
- `clone-state`
- undeclared `postselect`

Example program:

```lisp
(defintent demo.intent :priority 0.9 :confidence 0.8 "stabilize reasoning")
(observe obs.memory :source qso://memory/demo :basis ("claim" "context"))
(hypothesis hyp.bridge obs.memory)
(entangle obs.memory hyp.bridge :kind dependency :weight 0.7)
(project future.bridge :horizon 3 :using (qiskit pennylane cirq itensor))
(reason :goal demo.intent :return ranked-paths)
```

Compile a program:

```bash
qso-qlisp compile path/to/program.qlisp
```

Analyze and persist a trace:

```bash
qso-qlisp analyze path/to/program.qlisp --uri qso://quantum.state/my_reasoning_trace
```

Run the built-in demo:

```bash
./.venv/bin/python tools/qso_qlisp.py demo
```

Run reproducible local benchmarks:

```bash
qso-qlisp-bench --iterations 25
```

The analysis output includes:

- `compiled_ir`
- `fabric_report`
- `backend_reports`
- `reasoning_paths`
- `uncertainty_fields`
- `repair_proposals`
- `projection_candidates`
- `verification_hash`

Latest benchmark report:

- [`reports/quantum_lisp_benchmark_latest.md`](reports/quantum_lisp_benchmark_latest.md)

## Development Automation

Use one command entrypoint for repeatable local workflows:

```bash
qso-dev quick          # bootstrap cache + lint + core tests
qso-dev smoke          # runtime smoke stack
qso-dev all            # quick + smoke
qso-dev submission     # generate submission evidence bundle
qso-dev hook-install   # install pre-commit hook
```

Equivalent `make` targets:

```bash
make dev-quick
make dev-smoke
make dev-all
make dev-submission
make dev-hook-install
```

Notes:
- `qso-dev` reuses `.venv/` and caches dependency bootstrap based on `pyproject.toml` + `requirements.txt`.
- Set `QSO_DEV_FORCE_INSTALL=1` to force reinstall (`QSO_DEV_FORCE_INSTALL=1 qso-dev quick`).

## Solis Property Fraud Automation

Tokenize deed/grant events and compute deterministic fraud-risk scores:

```bash
solis-property-fraud run \
  --input data/deeds.jsonl \
  --output .codex/state/solis_property_fraud_scores.jsonl \
  --summary .codex/state/solis_property_fraud_summary.json
```

Incremental directory ingestion with checkpointing:

```bash
solis-property-fraud batch \
  --input-dir .codex/state/solis_property_deeds_inbox \
  --recursive \
  --output .codex/state/solis_property_fraud_scores.jsonl \
  --summary .codex/state/solis_property_fraud_summary.json \
  --checkpoint .codex/state/solis_property_fraud_checkpoint.json
```

Run with bundled synthetic data:

```bash
solis-property-fraud demo
```

Run via development automation wrapper:

```bash
qso-dev property-fraud
```

`qso-dev property-fraud` behavior:
- If `QSO_DEV_PROPERTY_FRAUD_INPUT_DIR` exists and has `.json/.jsonl`, it runs `solis-property-fraud batch`.
- Else if `QSO_DEV_PROPERTY_FRAUD_INPUT` exists, it runs `solis-property-fraud run`.
- Else it runs `solis-property-fraud demo`.

Optional environment overrides:

```bash
QSO_DEV_PROPERTY_FRAUD_INPUT_DIR=/path/to/inbox
QSO_DEV_PROPERTY_FRAUD_INPUT=/path/to/fallback_input.jsonl
QSO_DEV_PROPERTY_FRAUD_OUTPUT=/path/to/scores.jsonl
QSO_DEV_PROPERTY_FRAUD_SUMMARY=/path/to/summary.json
QSO_DEV_PROPERTY_FRAUD_CHECKPOINT=/path/to/checkpoint.json
QSO_DEV_PROPERTY_FRAUD_RESET_CHECKPOINT=1
QSO_DEV_PROPERTY_FRAUD_REPLACE_OUTPUT=1
```

Install a recurring cron job (default every 6 hours at minute 17):

```bash
tools/setup_solis_property_fraud_cron.sh
```

Override schedule when installing:

```bash
SOLIS_PROPERTY_FRAUD_CRON_SCHEDULE="5 * * * *" tools/setup_solis_property_fraud_cron.sh
```

## Orange County APN Database Automation

Build and maintain a full local APN SQLite database for Orange County, CA from the public OC GIS parcel layer:

```bash
solis-orange-county-apn-db sync \
  --endpoint https://ocgis.com/arcpub/rest/services/LegalLotsAttributeOpenData/FeatureServer/0 \
  --db .codex/state/orange_county_apn/apn_orange_county_ca.sqlite3 \
  --checkpoint .codex/state/orange_county_apn/checkpoint.json \
  --summary .codex/state/orange_county_apn/summary.json
```

Read local DB stats:

```bash
solis-orange-county-apn-db stats \
  --db .codex/state/orange_county_apn/apn_orange_county_ca.sqlite3
```

Run via development automation wrapper:

```bash
qso-dev apn-db
```

Optional env overrides:

```bash
QSO_DEV_OC_APN_ENDPOINT=https://ocgis.com/arcpub/rest/services/LegalLotsAttributeOpenData/FeatureServer/0
QSO_DEV_OC_APN_DB_PATH=/path/to/apn_orange_county_ca.sqlite3
QSO_DEV_OC_APN_CHECKPOINT_PATH=/path/to/checkpoint.json
QSO_DEV_OC_APN_SUMMARY_PATH=/path/to/summary.json
QSO_DEV_OC_APN_BATCH_SIZE=2000
QSO_DEV_OC_APN_MAX_BATCHES=25
QSO_DEV_OC_APN_RESET_CHECKPOINT=1
QSO_DEV_OC_APN_FULL_REFRESH=1
```

Compile full historical Solis scope (documents/maps/deeds/easements + `solis_id` states/transitions/anomalies):

```bash
solis-orange-county-scope run-all \
  --db .codex/state/orange_county_apn/apn_orange_county_ca.sqlite3 \
  --checkpoint .codex/state/orange_county_apn/history_checkpoint.json \
  --summary .codex/state/orange_county_apn/scope_summary.json
```

Development wrapper:

```bash
qso-dev apn-scope
```

Scope env overrides:

```bash
QSO_DEV_OC_SCOPE_SUMMARY_PATH=/path/to/scope_summary.json
QSO_DEV_OC_SCOPE_CHECKPOINT_PATH=/path/to/history_checkpoint.json
QSO_DEV_OC_SCOPE_BATCH_SIZE=2000
QSO_DEV_OC_SCOPE_MAX_BATCHES_PER_SOURCE=10
QSO_DEV_OC_SCOPE_RESET_CHECKPOINT=1
```

Export versioned Kaggle-ready datasets from the local Solis ledger:

```bash
pip install -e '.[dev,kaggle]'
solis-orange-county-kaggle-export \
  --db .codex/state/orange_county_apn/apn_orange_county_ca.sqlite3 \
  --output-root .codex/state/orange_county_apn/kaggle_exports
```

This writes an immutable release directory containing:
- `oc_apn_core.parquet`
- `oc_parcel_states.parquet`
- `oc_parcel_transitions.parquet`
- `oc_parcel_anomalies.parquet`
- `oc_risk_snapshot.parquet`
- `README.md`
- `manifest.json`

`oc_risk_snapshot` is a second-stage model derived from the full Solis state and transition history, not just current-row heuristics.

Use `--format jsonl` for a dependency-light local export when `pyarrow` is not installed.

Generate Kaggle metadata in the release directory:

```bash
solis-orange-county-kaggle-export \
  --db .codex/state/orange_county_apn/apn_orange_county_ca.sqlite3 \
  --output-root .codex/state/orange_county_apn/kaggle_exports \
  --kaggle-id alistaire/oc-parcel-intel \
  --kaggle-title "Solis Orange County APN Export"
```

Publish the generated release to Kaggle after export:

```bash
solis-orange-county-kaggle-export \
  --db .codex/state/orange_county_apn/apn_orange_county_ca.sqlite3 \
  --output-root .codex/state/orange_county_apn/kaggle_exports \
  --kaggle-id alistaire/oc-parcel-intel \
  --publish-kaggle \
  --kaggle-message "Release $(date -u +%Y-%m-%d)"
```

Run HTTP transport API:

```bash
python main.py --serve-http --seed-demo --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/healthz
```

Identity create route:

```bash
curl -X POST http://localhost:8000/v1/identity/create \
  -H 'content-type: application/json' \
  -d '{"identity_id":"demo_01","immutable_core":{"subject_ref":"demo_01"},"actor":"authority://root","policy_version":"v1"}'
```

## Governed Transport Layer

Transport is first-class state at `qso://infra.transport` and writes audit events to `.codex/state/network_audit.jsonl`.

CLI surface:

```bash
codexctl-transport status
codexctl-transport set tor --actor operator --policy-version v1
codexctl-transport health
codexctl-transport policy
```

By default:
- `research`: `direct|vpn|tor`
- `model_training`: `direct|vpn`
- `market_execution`: `direct|vpn` (Tor denied)

Docker/K8s transport manifests:
- `infra/docker/docker-compose.tor.yml`
- `infra/docker/docker-compose.vpn.yml`
- `infra/k8s/transport-sidecar.yaml`
- `infra/k8s/network-policy.yaml`

## Sandboxed MCP Education Server

Educational sandbox package lives at `mcp_qso_edu/` and enforces:
- URI rewriting into `qso://sandbox/<sandbox_id>/...`
- capability-scoped tools
- per-sandbox rate limits
- no access to production transport/identity/global registry roots

Run as stdio MCP server:

```bash
qso-edu-mcp-stdio
```

Persist sandbox operations to a custom path:

```bash
qso-edu-mcp-stdio --state-root .codex/state/mcp_qso_edu/sandboxes
```

Optional upstream MCP app bridge (explicit opt-in):

```bash
export QSO_EDU_UPSTREAM_APPS='{"example":["python3","/path/to/upstream_mcp.py"]}'
qso-edu-mcp-stdio --enable-upstream-apps
```

Local Plus-account relay bridge (same shared log for browser + MCP):

```bash
qso-plus-bridge-http --host 127.0.0.1 --port 8765
```

HTTPS mode:

```bash
qso-plus-bridge-http \
  --host 0.0.0.0 \
  --port 9443 \
  --tls-cert /path/to/fullchain.pem \
  --tls-key /path/to/privkey.pem
```

SOC2-style hardened mode (auth + origin + audit):

```bash
export QSO_BRIDGE_AUTH_TOKEN='replace-with-secret'
export QSO_BRIDGE_ALLOWED_ORIGIN='https://chat.example.com'
qso-plus-bridge-http \
  --host 0.0.0.0 \
  --port 9443 \
  --tls-cert /path/to/fullchain.pem \
  --tls-key /path/to/privkey.pem \
  --audit-log .codex/state/plus_bridge_access.jsonl \
  --max-requests-per-minute 120
```

POST messages:

```bash
curl -X POST https://127.0.0.1:9443/bridge/append \
  -H 'content-type: application/json' \
  -H "authorization: Bearer $QSO_BRIDGE_AUTH_TOKEN" \
  -d '{"source":"chatgpt_plus","content":"hello from plus"}'
```

Read messages:

```bash
curl -H "authorization: Bearer $QSO_BRIDGE_AUTH_TOKEN" \
  'https://127.0.0.1:9443/bridge/read?after_seq=0&limit=50'
```

Canonical chat tools (QSO source of truth):
- `qso.chat.open`
- `qso.chat.init`
- `qso.chat.append`
- `qso.chat.summarize`
- `qso.chat.verify`
- `qso.chat.read`
- `qso.chat.tail`
- `qso.chat.export_markdown`
- `qso.chat.fork`
- `qso.chat.subscribe` (Python API streaming)

APC education/dev tools (inside `mcp_qso_edu`):
- `qso.edu.apc.bootstrap` (runs all 10 tracks: reproducible audits, checklist, scorecards, teaching pipeline, crowdsweep pack, model comparison, artifact library, misinformation controls, scientific-method framework, red-team pack)
- `qso.edu.apc.runs`
- `qso.edu.apc.audit`
- `qso.edu.apc.resources`

Automatic Bayesian section in every `qso.edu.apc.bootstrap` bundle:
- `validation/apc_bayes_comparison_latest.json`
- `validation/apc_bayes_comparison_latest.md`
- includes prior-sensitivity matrix and Bayes-factor robustness band across APC prior families.

APC educational resources:
- `qso://edu/apc`

CLI for non-JSON-RPC execution:

```bash
qso-edu-apc-bootstrap \
  --session-token apc-community \
  --mode exhaustive \
  --domain physics \
  --baseline-models-csv 'LambdaCDM+SM,Toy-EFT,Phase-Only Baseline' \
  --publish-dir .codex/state/mcp_qso_edu/apc_published \
  --json-output .codex/state/mcp_qso_edu/apc_last_run.json
```

On-demand CI generation/publishing:
- Workflow: `.github/workflows/apc-edu-bundle.yml`
- Trigger: GitHub Actions -> `apc-edu-bundle` -> `Run workflow`

CLI bridges:
- `qso-chat <session_token> --author <name> --role <user|assistant|agent|system> --content "..."`
- `qso-chat <session_token> --tail 25`
- `qso-chat-ws --host 127.0.0.1 --port 8766` (read-only websocket tail viewer)

Quantum-safe + contract-anchored websocket mode:

```bash
export QSO_CHAT_WS_AUTH_TOKEN='replace-with-secret'
export QSO_CHAT_WS_PQ_SEED_HEX='0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'
export OQS_INSTALL_PATH='/path/to/liboqs/install'
qso-chat-ws \
  --host 0.0.0.0 \
  --port 9444 \
  --tls-cert /path/to/fullchain.pem \
  --tls-key /path/to/privkey.pem \
  --anchor-contract-address 0xYourSolisMerkleAnchorContract
```

Optional live on-chain anchoring (instead of deterministic tx-hash mode):

```bash
qso-chat-ws \
  --host 0.0.0.0 \
  --port 9444 \
  --tls-cert /path/to/fullchain.pem \
  --tls-key /path/to/privkey.pem \
  --anchor-contract-address 0xYourSolisMerkleAnchorContract \
  --anchor-rpc-url https://your-evm-rpc \
  --anchor-private-key 0x... \
  --anchor-live
```

Local one-command bootstrap (generates cert + token + PQ seed env file):

```bash
tools/setup_qso_chat_ws_hardened.sh
tools/run_qso_chat_ws_hardened.sh
```

NIST primitive requirement:
- `qso-chat-ws` quantum envelopes now require liboqs-backed `ML-DSA-65` + `ML-KEM-768`.
- Set `OQS_INSTALL_PATH` (or `QSO_CHAT_WS_OQS_INSTALL_PATH` in the hardened env file) to a liboqs install root containing `lib/liboqs*`.
- Hardened profile is fail-closed via:
  - `QSO_CHAT_WS_REQUIRE_TLS=1`
  - `QSO_CHAT_WS_REQUIRE_AUTH=1`
  - `QSO_CHAT_WS_REQUIRE_QUANTUM_ENVELOPE=1`
  - `QSO_CHAT_WS_REQUIRE_CONTRACT_ANCHOR=1`

Submission readiness bundle:

```bash
qso-dev submission
# writes .codex/state/submissions/<UTC_RUN_ID>/{manifest.json,summary.md,logs/*}
```

Upstream model MCP template:
- `tools/llm_mcp_server.py`
- `export QSO_EDU_UPSTREAM_APPS='{"llm":["python3","tools/llm_mcp_server.py"]}'`
- `qso-edu-mcp-stdio --enable-upstream-apps`

Sandbox persistence:
- operation log store at `.codex/state/mcp_qso_edu/sandboxes/*.ops.jsonl`
- all processes that reuse the same `session_token` replay the same persisted sandbox state

Compliance notes:
- See `docs/soc2_bridge_controls.md` for implemented controls and operating guidance.
- See `docs/soc2_socket_controls.md` for websocket security controls (WSS + PQ envelope + contract anchor).
- See `docs/submission_readiness.md` for evidence-bundle generation and submission checklist.
- See `docs/qso_fabric_edu_apc.md` for APC educational workflow and artifact contracts.

## Quantum Network Object Layer

Quantum-network scaffolding now exists for declarative, auditable QNO/QNSO workflows:
- Schemas: `api/schemas/quantum_*.schema.json` and `api/schemas/quantum_network_object.schema.json`
- Services: `services/quantum/*`
- MCP methods: `qso.quantum_create`, `qso.quantum_execute`, `qso.quantum_replay`, `qso.quantum_qjfp_handshake`, `qso.quantum_lisp_compile`, `qso.quantum_lisp_analyze`, `qso.quantum_lisp_replay`
- Spec docs: `docs/quantum_network_object_spec.md`, `docs/quantum_network_object_full_blueprint.md`
- Fabric kernel: `services/quantum/fabric/*` for patch-local states, restriction maps, overlap diagnostics, and gluing/coherence reports
- Demo: `./.venv/bin/python tools/qso_quantum_fabric_demo.py`
- Runtime demo: `./.venv/bin/python tools/qso_quantum_fabric_runtime_demo.py`
- Quantum LISP demo: `./.venv/bin/python tools/qso_qlisp.py demo`

Quantum object MVP modes:
- `object_kind="circuit_job"`: run backend-style circuit execution via `qso.quantum_execute`
- `object_kind="fabric"`: run local-to-global coherence/gluing analysis via the same `qso.quantum_execute` entry point
- `object_kind="quantum_lisp_program"`: compile and analyze descriptive Quantum LISP reasoning programs with `qso.quantum_lisp_analyze`
- `object_kind="reasoning_trace"`: persisted output of a Quantum LISP analysis, including compiled IR, fabric report, backend reports, ranked paths, uncertainty fields, repair proposals, and projections
- fabric objects can use `qso://quantum.fabric/*` URIs and carry a serialized `fabric_payload`

ITensor integration notes:
- Backend id: `itensor`
- Runtime path: `services/quantum/backends/itensor_backend.py`
- If `QSO_ITENSOR_RUNNER` is set, the backend shells out to an external ITensor runner and expects JSON on stdout.
- If `QSO_ITENSOR_RUNNER` is not set, the backend falls back to the deterministic local statevector simulator in `services/quantum/simulators/statevector.py`.
- Websocket tail responses can attach quantum filter envelopes with `QSO_CHAT_WS_ITENSOR_FILTER=1`.
- Fail-closed websocket filtering is available with `QSO_CHAT_WS_REQUIRE_ITENSOR_FILTER=1`.

## Execution Baseline

All project commands are expected to run via the local virtualenv binaries:

- `make test` -> `.venv/bin/python -m pytest`
- `make lint` -> `.venv/bin/python -m ruff check .`
- `make bench` -> `.venv/bin/python cmd/qso-node/benchmark_cli.py`

## Core Principle

Primary storage is live state in the QSO runtime.
QFF (`.qff`) is export/snapshot only.

## Transport Surfaces

- REST adapter: `api/rest`
- gRPC-style adapter: `api/grpc`
- WebSocket adapter: `api/websocket`

## Storage/Federation Primitives

- Event store: `storage/event_store`
- Checkpoint store: `storage/checkpoint_store`
- Snapshot store: `storage/snapshot_store`
- Sharding/replication helpers: `federation/sharding`, `federation/replication`

## Pilot Architecture

- Sovereign identity pilot build sheet: `docs/sovereign_identity_pilot_build_sheet.md`

## Solis Versioning

- Canonical conventions: `solis/reports/versioning_conventions.md`
- Runtime helpers: `solis/schemas/versioning.py`
