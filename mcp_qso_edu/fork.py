from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4


def fork_conversation(qso, sandbox_id: str, source_uri: str) -> dict[str, Any]:
    parent = qso.read(sandbox_id, source_uri)
    fork_id = str(uuid4())
    fork_uri = f"{source_uri}/fork/{fork_id}"

    forked = deepcopy(parent)
    forked_meta = dict(forked.get("meta", {}))
    forked_meta.update({"forked_from": source_uri, "fork_id": fork_id})
    forked["meta"] = forked_meta

    qso.create(
        sandbox_id=sandbox_id,
        uri=fork_uri,
        schema=None,
        initial=forked,
    )
    return {"uri": fork_uri, "fork_id": fork_id}
