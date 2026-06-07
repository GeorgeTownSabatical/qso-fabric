# SOC2 Bridge Controls

This document describes operational controls implemented for the `qso-plus-bridge-http` relay.
It is an engineering control map, not a SOC 2 attestation report.

## Implemented Controls

1. Transport encryption in transit
- HTTPS supported with `--tls-cert` + `--tls-key`.
- TLS minimum version enforced at 1.2.

2. Logical access control
- Optional bearer-token enforcement via `--auth-token` or `QSO_BRIDGE_AUTH_TOKEN`.
- Requests without valid token receive `401`.

3. Network request governance
- Per-IP request limiting with `--max-requests-per-minute`.
- Oversubscription receives `429`.
- Request body size capped by `--max-body-bytes`.

4. Security header baseline
- `Cache-Control: no-store`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `X-Frame-Options: DENY`
- CORS can be restricted with exact `--allowed-origin` / `QSO_BRIDGE_ALLOWED_ORIGIN`.

5. Auditability
- Structured access logs are appended to `--audit-log` (default `.codex/state/plus_bridge_access.jsonl`).
- Each entry captures timestamp, request id, client ip, method, path, status, and detail.

## Operational Guidance

1. Use HTTPS in any non-local environment.
2. Set a strong auth token and rotate it periodically.
3. Restrict `--allowed-origin` to the exact UI origin.
4. Store audit logs on protected disk and include them in retention policy.
5. Monitor for repeated `401`, `429`, and `5xx` responses.

## Example Hardened Launch

```bash
export QSO_BRIDGE_AUTH_TOKEN='replace-with-secret'
export QSO_BRIDGE_ALLOWED_ORIGIN='https://chat.example.com'
qso-plus-bridge-http \
  --host 0.0.0.0 \
  --port 9443 \
  --tls-cert /path/to/fullchain.pem \
  --tls-key /path/to/privkey.pem \
  --audit-log .codex/state/plus_bridge_access.jsonl \
  --max-requests-per-minute 120 \
  --max-body-bytes 65536
```
