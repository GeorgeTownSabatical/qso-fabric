# Submission Readiness

This document defines the local evidence workflow for security/compliance submission prep.

## Preconditions

- Hardened websocket env exists at `.codex/state/qso_chat_ws.env`.
- `QSO_CHAT_WS_OQS_INSTALL_PATH` points to a valid liboqs install root (`lib/liboqs*`).
- Fail-closed gates are enabled:
  - `QSO_CHAT_WS_REQUIRE_TLS=1`
  - `QSO_CHAT_WS_REQUIRE_AUTH=1`
  - `QSO_CHAT_WS_REQUIRE_QUANTUM_ENVELOPE=1`
  - `QSO_CHAT_WS_REQUIRE_CONTRACT_ANCHOR=1`

## Generate Evidence Bundle

```bash
qso-dev submission
```

Output directory:

```text
.codex/state/submissions/<UTC_RUN_ID>/
  manifest.json
  summary.md
  logs/
```

## Bundle Contents

- `manifest.json`
  - command execution results and return codes
  - environment metadata (Python/platform/liboqs path)
  - SHA-384 hashes of critical control files
- `summary.md`
  - pass/fail status and key command traces
- `logs/*.log`
  - stdout/stderr per command

## Deterministic Verification Scope

- Dev gates: lint + test + smoke (`qso-dev quick`, `qso-dev smoke`)
- Security gates:
  - `tests/test_pq_keys_nist.py`
  - `tests/test_quantum_socket_hardening.py`
  - `tests/test_qso_chat_ws_security.py`
  - `tests/test_plus_bridge_https.py`
  - `tests/test_anchor_adapters.py`
- Live hardened runtime probe:
  - `tools/verify_hardened_wss.py`

## Known Submission Note

- Current local runtime may emit a warning if `liboqs` and `liboqs-python` minor versions differ (for example `0.15.x` vs `0.14.x`).
- Functionality remains validated by tests, but align versions before external attestation packages.
