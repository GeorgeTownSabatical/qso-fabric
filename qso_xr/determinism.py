from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_render_payload(render_payload: Dict[str, Any]) -> Dict[str, Any]:
    stable = deepcopy(render_payload)
    # Frame index is runtime-local and should not affect deterministic scene content hashing.
    stable.pop("frame", None)
    stable.pop("source", None)
    return stable


def deterministic_frame_hash(render_payload: Dict[str, Any]) -> str:
    return sha256_hex(stable_render_payload(render_payload))
