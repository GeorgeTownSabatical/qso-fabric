# API

Contains typed schemas and MCP tool adapters.

Required MCP surface:
- `qso.create(uri, schema)`
- `qso.read(uri)`
- `qso.patch(uri, delta)`
- `qso.subscribe(uri)`
- `qso.export_snapshot(uri)`
- `qso.import_snapshot(qff)`
- `qso.entangle(uriA, uriB, relationship)`
- `qso.timeline(uri)`
- `qso.identity_create(uri, immutable_core, actor, policy_version, node_id)`
- `qso.identity_event(uri, event_type, payload, actor, policy_version, node_id)`
- `qso.identity_state(uri, strict=True)`
- `qso.identity_authority_create(uri, immutable_core, actor, policy_version, node_id)`
- `qso.identity_authority_issue_credential(uri, credential_id, credential_body, actor, policy_version, node_id)`
- `qso.identity_authority_revoke_credential(uri, credential_id, reason, actor, policy_version, node_id)`
- `qso.identity_authority_publish_policy(policy, actor, node_id)`
- `qso.identity_authority_policy_current()`
- `qso.identity_export_bundle(uri, trust_roots, strict=True)`
- `qso.identity_bundle_sign(bundle)`
- `qso.identity_verify_bundle(bundle, strict_archival=True, reject_archived=True)`
