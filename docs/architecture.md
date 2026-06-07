# Architecture

QSO Fabric is a live event-sourced state runtime:
- primary storage: live QSO objects in runtime
- export layer: QFF snapshot files
- MCP tool surface for create/read/patch/subscribe/timeline/entangle/export/import
- GDML for cross-node reward/policy optimization
