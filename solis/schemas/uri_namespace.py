from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from solis.shared.canonical_json import canonical_json
from solis.shared.hashing import sha256_hex_text

URI_NAMESPACE_MAP_V1_PATH = Path(__file__).with_name("uri_namespace_map.v1.json")

REQUIRED_PREFIXES = {
    "qso://identity.person.",
    "qso://solis.star.",
    "qso://solis.constellation.",
    "qso://solis.stellar_event.",
    "qso://solis.anchor.",
    "qso://solis.rbac.",
    "qso://solis.policy.",
}


def load_uri_namespace_map(path: Path | None = None) -> dict[str, Any]:
    target = path or URI_NAMESPACE_MAP_V1_PATH
    loaded = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("uri namespace map must be a JSON object")
    return loaded


def uri_namespace_hash(namespace_map: dict[str, Any]) -> str:
    payload = dict(namespace_map)
    audit = dict(payload.get("audit", {})) if isinstance(payload.get("audit"), dict) else {}
    audit.pop("canonical_hash", None)
    payload["audit"] = audit
    return sha256_hex_text(canonical_json(payload))


def validate_uri_namespace_map(namespace_map: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(namespace_map.get("schema_version", "")) != "1.0":
        errors.append("schema_version must be '1.0'")
    if not str(namespace_map.get("map_version", "")).startswith("v"):
        errors.append("map_version must start with 'v'")

    entries = namespace_map.get("entries")
    if not isinstance(entries, list):
        errors.append("entries must be a list")
        return errors

    prefixes: set[str] = set()
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entries[{idx}] must be an object")
            continue
        prefix = str(entry.get("uri_prefix", "")).strip()
        domain = str(entry.get("domain", "")).strip()
        if not domain:
            errors.append(f"entries[{idx}] missing domain")
        if not prefix.startswith("qso://"):
            errors.append(f"entries[{idx}] invalid uri_prefix")
            continue
        if prefix in prefixes:
            errors.append(f"duplicate uri_prefix: {prefix}")
        prefixes.add(prefix)

    missing = sorted(REQUIRED_PREFIXES - prefixes)
    if missing:
        errors.append(f"missing required uri prefixes: {','.join(missing)}")

    return errors


def sync_audit_hash(namespace_map: dict[str, Any]) -> dict[str, Any]:
    rendered = dict(namespace_map)
    audit = dict(rendered.get("audit", {})) if isinstance(rendered.get("audit"), dict) else {}
    audit["hash_algo"] = "sha256"
    audit["canonical_hash"] = uri_namespace_hash(rendered)
    rendered["audit"] = audit
    return rendered
