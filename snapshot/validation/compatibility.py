from __future__ import annotations


def snapshot_compatible(snapshot_header: dict, runtime_version: str) -> bool:
    return str(snapshot_header.get("runtime_version", "")) == runtime_version
