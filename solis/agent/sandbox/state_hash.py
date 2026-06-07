from __future__ import annotations

from typing import Any, cast

from solis.shared.hashing import sha256_hex_obj


def state_hash(state: Any) -> str:
    return cast(str, sha256_hex_obj(state))
