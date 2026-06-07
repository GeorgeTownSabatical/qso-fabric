# JS SDK

Minimal HTTP client:

- `client.mjs`

Example:

```js
import { QSOClient } from "./client.mjs";

const client = new QSOClient("http://localhost:8000");
const created = await client.createIdentity("js_demo", { subject_ref: "js_demo" });
console.log(created);
```

Planned:
- ESM client for MCP-compatible endpoints
- streaming subscriptions over SSE/WebSocket
- typed interfaces for QSO operations
