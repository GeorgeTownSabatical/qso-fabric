# SOC2 Socket Controls

This document describes security controls implemented for `qso-chat-ws` when operated in hardened mode.
It is an engineering control map, not a SOC 2 attestation report.

## Implemented Controls

1. Transport encryption in transit
- WSS enabled with `--tls-cert` + `--tls-key`.
- TLS minimum version enforced at 1.2.

2. Logical access control
- Optional websocket auth token via `--auth-token` or `QSO_CHAT_WS_AUTH_TOKEN`.
- Unauthorized requests are rejected.

3. Quantum-safe envelope profile
- Outbound payloads can be signed with a liboqs-backed NIST profile using:
  - `ML-DSA-65` signatures
  - `ML-KEM-768` KEM profile metadata
  - `SHA-384` canonical payload hash
- Enable with `--pq-seed-hex` or `--pq-private-key`.
- Set `OQS_INSTALL_PATH` (or `QSO_CHAT_WS_OQS_INSTALL_PATH` in hardened env) to a liboqs installation root.
- Fail-closed mode is enabled with:
  - `QSO_CHAT_WS_REQUIRE_TLS=1`
  - `QSO_CHAT_WS_REQUIRE_AUTH=1`
  - `QSO_CHAT_WS_REQUIRE_QUANTUM_ENVELOPE=1`
  - `QSO_CHAT_WS_REQUIRE_CONTRACT_ANCHOR=1`

4. Solidity contract anchoring
- Socket payload hashes can be anchored against a Solidity Merkle anchor contract.
- Deterministic mode is default (signed tx hash simulation, no submit).
- Live anchoring is opt-in with `--anchor-live` + RPC + private key.

5. Security telemetry surface
- `handshake` request exposes active transport/security capabilities for clients.
- Tail responses include `_qso_security` envelope when signing/anchoring is enabled.

## Hardened Launch Example

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

## Local Bootstrap

```bash
tools/setup_qso_chat_ws_hardened.sh
tools/run_qso_chat_ws_hardened.sh
```
