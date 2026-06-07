from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping


def structured_log(level: str, message: str, **fields: Any) -> str:
    payload: Mapping[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level.lower(),
        "message": message,
        **fields,
    }
    line = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    print(line)
    return line
