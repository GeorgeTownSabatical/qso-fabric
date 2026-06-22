# QSO API

## Source

- Path: `qso-api.md`
- SHA-256: `a17c81d6ec0be348d909d3f0176ae7a2e541973446fc883180da1578cd85c009`
- Word count: `308`

## Summary

# QSO API Tool endpoints: - `qso.create(uri, schema)` - `qso.read(uri)` - `qso.patch(uri, delta)` - `qso.subscribe(uri, cursor=None, backpressure="block", queue_size=512)` - `qso.subscribe_prefix(uri_prefix, cursor=None, backpressure="block", queue_size=512)` - `qso.subscribe_projection(uri, viewpoint=None, radius=150.0, cursor=None, backpressure="drop_oldest", queue_size=256)` - `qso.export_snapshot(uri)` - `qso.import_snapshot(qff)` - `qso.entangle(uriA, uriB, relationship)` - `qso.timeline(uri)` - `qso.cursor_encode_uri(uri, next_event_index)` - `qso.cursor_encode_prefix(uri_prefix, next_by_uri)` - `qso.cursor_decode(token)` - `qso.transport_set(mode, actor="transport-controller", policy_version="v1", node_id="local")` - `qso.transport_status()` - `qso.transport_health()` - `qso.transport_policy()` - `qso.transport_metrics()` - `qso.transport_send(workload_type, method, url, headers=None, body=None, actor="transport-client", policy_version="v1", node_id="local", timeout_seconds=10.0, metadata=None)` - `qso.quantum_create(uri, payload, actor="quantum-author", policy_version="v1", node_id="local")` - `qso.quantum_execute(uri, actor="quantum-manager", policy_version="v1", node_id="local")` - `qso.quantum_replay(uri, strict=True)` - `qso.quantum_lisp_compile(source, metadata=None)` -...

## Keywords

`qso`, `uri`, `actor`, `policy_version`, `node_id`, `local`, `none`, `true`, `authority`, `quantum`, `strict`, `object_kind`

## Related Pages

- [[qso-fabric]]

## Raw Excerpt

```text
# QSO API Tool endpoints: - `qso.create(uri, schema)` - `qso.read(uri)` - `qso.patch(uri, delta)` - `qso.subscribe(uri, cursor=None, backpressure="block", queue_size=512)` - `qso.subscribe_prefix(uri_prefix, cursor=None, backpressure="block", queue_size=512)` - `qso.subscribe_projection(uri, viewpoint=None, radius=150.0, cursor=None, backpressure="drop_oldest", queue_size=256)` - `qso.export_snapshot(uri)` - `qso.import_snapshot(qff)` - `qso.entangle(uriA, uriB, relationship)` - `qso.timeline(uri)` - `qso.cursor_encode_uri(uri, next_event_index)` - `qso.cursor_encode_prefix(uri_prefix, next_by_uri)` - `qso.cursor_decode(token)` - `qso.transport_set(mode, actor="transport-controller", policy_version="v1", node_id="local")` - `qso.transport_status()` - `qso.transport_health()` - `qso.transport_policy()` - `qso.transport_metrics()` - `qso.transport_send(workload_type, method, url, headers=None, body=None, actor="transport-client", policy_version="v1", node_id="local", timeout_seconds=10.0, metadata=None)` - `qso.quantum_create(uri, payload, actor="quantum-author", policy_version="v1", node_id="local")` - `qso.quantum_execute(uri, actor="quantum-manager", policy_version="v1", node_id="local")` - `qso.quantum_replay(uri, strict=True)` - `qso.quantum_lisp_compile(source, metadata=None)` - `qso.quantum_lisp_analyze(uri, actor="quantum-lisp", policy_version="v1", node_id="local")` - `qso.quantum_lisp_replay(uri, strict=True)` - `qso.quantum_qjfp_handshake(node_identity, hardware_signature, policy_version, quantum_capabilities)` Quantum object modes: - circuit execution: set `object_kind="circuit_job"` or omit it and provide `backend`, `qubit_count`, `circuit_spec`, `measurement_schema` - fabric execution: set `object_kind="fabric"` and provide `fabric_payload` plus optional `coherence_threshold` - Quantum LISP reasoning: set `object_kind="quantum_lisp_program"`, `backend="quantum_lisp"`, and provide `source` - reasoning traces: `qso.quantum_lisp_analyze` patches the object to `object_kind="reasoning_trace"` with `compiled_ir` and `reasoning_report` - fabric-oriented URI families may use `qso://quantum.patch/*`,...
```
