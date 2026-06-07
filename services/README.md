# Services

Microservices and domain services for the QSO runtime:
- `registry`: URI-first object catalog
- `state_engine`: event-sourced state mutation and replay
- `event_log`: append-only timeline storage and audit
- `entanglement_graph`: dependency links + stream propagation
- `snapshot_exporter`: QFF export/import
- `crypto_access`: signing and verification
- `meta_learning`: local autonomous optimization suggestions
- `transport`: governed transport abstraction layer (direct/vpn/tor), policy gates, audit chain, and health telemetry
- `identity_authority`: authority-side identity lifecycle and policy hooks
- `identity_verifier`: strict identity bundle verification and deterministic replay checks
