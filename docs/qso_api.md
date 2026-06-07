# QSO API

Tool endpoints:
- `qso.create(uri, schema)`
- `qso.read(uri)`
- `qso.patch(uri, delta)`
- `qso.subscribe(uri, cursor=None, backpressure="block", queue_size=512)`
- `qso.subscribe_prefix(uri_prefix, cursor=None, backpressure="block", queue_size=512)`
- `qso.subscribe_projection(uri, viewpoint=None, radius=150.0, cursor=None, backpressure="drop_oldest", queue_size=256)`
- `qso.export_snapshot(uri)`
- `qso.import_snapshot(qff)`
- `qso.entangle(uriA, uriB, relationship)`
- `qso.timeline(uri)`
- `qso.cursor_encode_uri(uri, next_event_index)`
- `qso.cursor_encode_prefix(uri_prefix, next_by_uri)`
- `qso.cursor_decode(token)`
- `qso.transport_set(mode, actor="transport-controller", policy_version="v1", node_id="local")`
- `qso.transport_status()`
- `qso.transport_health()`
- `qso.transport_policy()`
- `qso.transport_metrics()`
- `qso.transport_send(workload_type, method, url, headers=None, body=None, actor="transport-client", policy_version="v1", node_id="local", timeout_seconds=10.0, metadata=None)`
- `qso.quantum_create(uri, payload, actor="quantum-author", policy_version="v1", node_id="local")`
- `qso.quantum_execute(uri, actor="quantum-manager", policy_version="v1", node_id="local")`
- `qso.quantum_replay(uri, strict=True)`
- `qso.quantum_qjfp_handshake(node_identity, hardware_signature, policy_version, quantum_capabilities)`

Quantum object modes:
- circuit execution: set `object_kind="circuit_job"` or omit it and provide `backend`, `qubit_count`, `circuit_spec`, `measurement_schema`
- fabric execution: set `object_kind="fabric"` and provide `fabric_payload` plus optional `coherence_threshold`
- fabric-oriented URI families may use `qso://quantum.patch/*`, `qso://quantum.overlap/*`, and `qso://quantum.fabric/*`
- `qso.identity_create(uri, immutable_core, actor="authority", policy_version="v1", node_id="local")`
- `qso.identity_event(uri, event_type, payload, actor="authority", policy_version="v1", node_id="local")`
- `qso.identity_state(uri, strict=True)`
- `qso.identity_authority_create(uri, immutable_core, actor="authority", policy_version="v1", node_id="local")`
- `qso.identity_authority_issue_credential(uri, credential_id, credential_body=None, actor="authority", policy_version="v1", node_id="local")`
- `qso.identity_authority_revoke_credential(uri, credential_id, reason, actor="authority", policy_version="v1", node_id="local")`
- `qso.identity_authority_publish_policy(policy, actor="authority", node_id="local")`
- `qso.identity_authority_policy_current()`
- `qso.identity_export_bundle(uri, trust_roots=None, strict=True)`
- `qso.identity_bundle_sign(bundle)`
- `qso.identity_verify_bundle(bundle, strict_archival=True, reject_archived=True)`

WebXR adapter surface (`tools/qso_web_api.py`):
- `WebXRAdapter.stream_projection_sse(...)`
- `WebXRAdapter.stream_projection_ws(...)`
- `WebXRAdapter.apply_action(uri, action, ...)`
- `QSOAPI.handle_request(route="xr.apply_action", ...)`
