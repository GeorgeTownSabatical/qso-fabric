# Rust SDK

Minimal crate located in this directory.

Build:

```bash
cd sdk/rust
cargo build
```

Use:

```rust
use qso_fabric_sdk::QsoClient;
use serde_json::json;

let client = QsoClient::new("http://localhost:8000");
let created = client.create_identity("rust_demo", json!({"subject_ref":"rust_demo"}), "authority", "v1")?;
println!("{}", created.object_uri);
```

Planned:
- async MCP transport
- typed QSO models via serde
- stream subscription adapters
