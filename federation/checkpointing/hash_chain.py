from __future__ import annotations

import hashlib
import json


def checkpoint_hash(events: list[dict]) -> str:
    payload = json.dumps(events, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
