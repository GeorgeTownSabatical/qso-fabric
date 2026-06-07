from __future__ import annotations

from solis.schemas.uri_namespace import (
    REQUIRED_PREFIXES,
    load_uri_namespace_map,
    uri_namespace_hash,
    validate_uri_namespace_map,
)


def test_uri_namespace_map_is_valid_and_complete() -> None:
    namespace_map = load_uri_namespace_map()
    errors = validate_uri_namespace_map(namespace_map)
    assert errors == []

    entries = namespace_map["entries"]
    prefixes = {str(entry["uri_prefix"]) for entry in entries}
    assert REQUIRED_PREFIXES.issubset(prefixes)


def test_uri_namespace_map_hash_is_stable_and_auditable() -> None:
    namespace_map = load_uri_namespace_map()
    expected_hash = str(namespace_map.get("audit", {}).get("canonical_hash", ""))
    assert expected_hash
    assert uri_namespace_hash(namespace_map) == expected_hash
