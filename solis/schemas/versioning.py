from __future__ import annotations

from dataclasses import dataclass

SCHEMA_VERSION = "1.0"
MODEL_VERSION = "1.0"
COMPILER_VERSION = "1.0"
POLICY_VERSION = "v1"


@dataclass(frozen=True)
class VersionEnvelope:
    schema_version: str = SCHEMA_VERSION
    model_version: str | None = None
    compiler_version: str | None = None
    policy_version: str | None = None


def parse_semver(version: str) -> tuple[int, int]:
    text = str(version).strip()
    parts = text.split(".")
    if len(parts) != 2:
        raise ValueError(f"version must be major.minor, got '{version}'")
    major = int(parts[0])
    minor = int(parts[1])
    if major < 0 or minor < 0:
        raise ValueError(f"version components must be non-negative, got '{version}'")
    return major, minor


def is_backward_compatible(current: str, candidate: str) -> bool:
    current_major, current_minor = parse_semver(current)
    candidate_major, candidate_minor = parse_semver(candidate)
    if current_major != candidate_major:
        return False
    return candidate_minor >= current_minor
