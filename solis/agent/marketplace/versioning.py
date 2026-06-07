from __future__ import annotations


def bump_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("version must be semver-like: X.Y.Z")
    major, minor, patch = map(int, parts)
    patch += 1
    return f"{major}.{minor}.{patch}"
